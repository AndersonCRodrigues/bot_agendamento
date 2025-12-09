from typing import List, Dict, Any, Optional
from bson import ObjectId
import logging
from ..database import mongodb, cache
from ..schemas import CompanyKnowledgeBase
from ..models import FAQResponse
from .openai_service import openai_service
from ..config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Serviço de RAG - Retrieval Augmented Generation"""

    def __init__(self):
        self.collection_name = CompanyKnowledgeBase.collection_name

    async def vector_search(
        self, query: str, company_id: str, top_k: int = None, min_score: float = None
    ) -> List[FAQResponse]:
        """
        Busca vetorial no knowledge base

        Args:
            query: Pergunta/query do usuário
            company_id: ID da empresa
            top_k: Número de resultados (default: settings.RAG_TOP_K)
            min_score: Score mínimo de relevância (default: settings.RAG_MIN_SCORE)

        Returns:
            Lista de FAQs relevantes com scores
        """
        try:
            top_k = top_k or settings.RAG_TOP_K
            min_score = min_score or settings.RAG_MIN_SCORE

            logger.info(
                f"[RAG] Iniciando busca: query='{query[:50]}...', company={company_id}"
            )
            logger.debug(f"[RAG] Parâmetros: top_k={top_k}, min_score={min_score}")

            # Verifica cache
            cache_key = f"rag:{company_id}:{query[:50]}"
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"[RAG] ✅ Cache hit - {len(cached)} FAQs retornadas")
                return cached

            # Gera embedding da query
            logger.debug("[RAG] Gerando embedding da query...")
            query_embedding = await openai_service.get_embedding(query)
            logger.debug(f"[RAG] Embedding gerado: dimensão {len(query_embedding)}")

            # Busca vetorial no MongoDB Atlas
            db = mongodb.get_database()
            collection = db[self.collection_name]

            # Primeiro, verifica se existem documentos da empresa
            doc_count = await collection.count_documents(
                {"company_id": company_id, "is_active": True}
            )
            logger.info(f"[RAG] 📊 Total de FAQs ativas na base: {doc_count}")

            if doc_count == 0:
                logger.warning(
                    f"[RAG] ⚠️ Nenhuma FAQ encontrada para company_id={company_id}"
                )
                return []

            # Pipeline de agregação com vector search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "knowledge_vector_index",  # Nome do índice no Atlas
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": top_k * 10,  # Busca 10x para filtrar
                        "limit": top_k * 2,
                        "filter": {"company_id": company_id, "is_active": True},
                    }
                },
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
                {"$match": {"score": {"$gte": min_score}}},
                {
                    "$project": {
                        "question": "$metadata.question",
                        "answer": "$metadata.answer",
                        "category": "$metadata.category",
                        "score": 1,
                    }
                },
                {"$limit": top_k},
            ]

            logger.debug(f"[RAG] Executando pipeline de agregação...")

            try:
                cursor = collection.aggregate(pipeline)
                results = await cursor.to_list(length=top_k)
                logger.info(
                    f"[RAG] 🔍 Vector search retornou {len(results)} resultados"
                )

                # Se não encontrou nada, tenta com score mais baixo
                if len(results) == 0 and min_score > 0.3:
                    logger.warning(
                        f"[RAG] 🔄 Nenhum resultado com min_score={min_score}, tentando com 0.3..."
                    )
                    pipeline[2] = {"$match": {"score": {"$gte": 0.3}}}
                    cursor = collection.aggregate(pipeline)
                    results = await cursor.to_list(length=top_k)
                    logger.info(f"[RAG] 🔍 Retry retornou {len(results)} resultados")

                # Se AINDA não encontrou, usa fallback sem score
                if len(results) == 0:
                    logger.warning(
                        "[RAG] 🔄 Vector search vazio, tentando fallback sem filtro de score..."
                    )
                    pipeline[2] = {"$match": {}}  # Remove filtro de score
                    cursor = collection.aggregate(pipeline)
                    results = await cursor.to_list(length=top_k)
                    logger.info(
                        f"[RAG] 🔍 Fallback sem score retornou {len(results)} resultados"
                    )
            except Exception as vector_error:
                # Se o vector search falhar (índice não existe), faz busca fallback
                logger.error(f"[RAG] ❌ Vector search falhou: {vector_error}")
                logger.warning("[RAG] 🔄 Tentando busca fallback sem vector search...")

                # Fallback: busca simples por palavras-chave
                results = await self._fallback_search(
                    collection, query, company_id, top_k
                )
                logger.info(f"[RAG] Fallback retornou {len(results)} resultados")

            # Converte para FAQResponse
            faqs = []
            for r in results:
                try:
                    faq = FAQResponse(
                        question=r["question"],
                        answer=r["answer"],
                        category=r.get("category", "geral"),
                        relevance_score=r.get("score", 0.5),  # Score padrão no fallback
                    )
                    faqs.append(faq)
                    logger.info(
                        f"[RAG]   ✓ FAQ: '{faq.question[:60]}...' (score: {faq.relevance_score:.3f})"
                    )
                    logger.debug(f"[RAG]     Resposta: '{faq.answer[:80]}...'")
                except Exception as parse_error:
                    logger.error(f"[RAG] Erro ao parsear FAQ: {parse_error}, doc: {r}")
                    continue

            # Cacheia resultado (1 hora)
            if faqs:
                cache.set(cache_key, faqs, ttl_seconds=3600)
                logger.info(f"[RAG] ✅ {len(faqs)} FAQs encontradas e cacheadas")
            else:
                logger.warning(
                    f"[RAG] ⚠️ Nenhuma FAQ relevante encontrada (min_score={min_score})"
                )

            return faqs

        except Exception as e:
            logger.error(f"[RAG] ❌ Erro na busca vetorial: {e}", exc_info=True)
            # Retorna lista vazia em caso de erro (não quebra o fluxo)
            return []

    async def _fallback_search(
        self, collection, query: str, company_id: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Busca fallback usando text search ou regex quando vector search não está disponível
        """
        try:
            logger.info(f"[RAG FALLBACK] Buscando FAQs para: '{query[:50]}...'")

            # Busca simples por palavras-chave na question e answer
            query_lower = query.lower()
            keywords = query_lower.split()[:5]  # Primeiras 5 palavras

            # Remove stopwords
            stopwords = [
                "como",
                "para",
                "faço",
                "fazer",
                "é",
                "um",
                "uma",
                "o",
                "a",
                "de",
                "do",
                "da",
            ]
            keywords = [kw for kw in keywords if len(kw) > 3 and kw not in stopwords]

            logger.debug(f"[RAG FALLBACK] Keywords extraídas: {keywords}")

            if not keywords:
                # Se não há keywords, retorna TODAS as FAQs da empresa
                logger.warning(
                    "[RAG FALLBACK] Sem keywords válidas, retornando todas FAQs"
                )
                cursor = collection.find(
                    {"company_id": company_id, "is_active": True},
                    {
                        "metadata.question": 1,
                        "metadata.answer": 1,
                        "metadata.category": 1,
                    },
                ).limit(top_k)
            else:
                # Constrói regex para buscar pelas palavras
                regex_pattern = "|".join([f"(?i){kw}" for kw in keywords])

                logger.debug(f"[RAG FALLBACK] Regex pattern: {regex_pattern}")

                cursor = collection.find(
                    {
                        "company_id": company_id,
                        "is_active": True,
                        "$or": [
                            {"metadata.question": {"$regex": regex_pattern}},
                            {"metadata.answer": {"$regex": regex_pattern}},
                            {"metadata.keywords": {"$in": keywords}},
                        ],
                    },
                    {
                        "metadata.question": 1,
                        "metadata.answer": 1,
                        "metadata.category": 1,
                    },
                ).limit(top_k)

            docs = await cursor.to_list(length=top_k)

            # Formata resultado similar ao vector search
            results = []
            for doc in docs:
                results.append(
                    {
                        "question": doc["metadata"]["question"],
                        "answer": doc["metadata"]["answer"],
                        "category": doc["metadata"].get("category", "geral"),
                        "score": 0.6,  # Score fixo alto para fallback
                    }
                )
                logger.debug(
                    f"[RAG FALLBACK]   ✓ Encontrou: '{doc['metadata']['question'][:50]}...'"
                )

            logger.info(f"[RAG FALLBACK] ✅ {len(results)} FAQs encontradas")
            return results

        except Exception as e:
            logger.error(
                f"[RAG FALLBACK] ❌ Erro no fallback search: {e}", exc_info=True
            )
            return []

    def format_for_prompt(self, faqs: List[FAQResponse]) -> str:
        """
        Formata FAQs para inserir no prompt do agente

        Args:
            faqs: Lista de FAQs recuperadas

        Returns:
            String formatada para o prompt
        """
        if not faqs:
            logger.warning(
                "[RAG] ⚠️ Nenhuma FAQ para formatar - retornando mensagem vazia"
            )
            return "Nenhum conhecimento específico encontrado na base."

        logger.info(f"[RAG] 📝 Formatando {len(faqs)} FAQs para o prompt")

        formatted = "=== CONHECIMENTO DA BASE (FAQ) ===\n\n"
        for i, faq in enumerate(faqs, 1):
            formatted += f"FAQ #{i}:\n"
            formatted += f"Pergunta: {faq.question}\n"
            formatted += f"Resposta: {faq.answer}\n"
            formatted += (
                f"Categoria: {faq.category} | Relevância: {faq.relevance_score:.2f}\n\n"
            )

        formatted += "=== FIM DO CONHECIMENTO ===\n"
        formatted += "INSTRUÇÕES: Use as informações acima para responder o cliente. "
        formatted += "Se a pergunta do cliente corresponder a alguma FAQ acima, USE essa resposta diretamente. "
        formatted += "NÃO invente informações que não estão nas FAQs acima."

        logger.debug(f"[RAG] Prompt formatado com {len(formatted)} caracteres")
        return formatted

    async def create_knowledge(
        self, company_id: str, question: str, answer: str, category: str, priority: int
    ) -> str:
        """
        Cria nova entrada no knowledge base

        Returns:
            ID da entrada criada
        """
        try:
            logger.info(f"[RAG] Criando FAQ: '{question[:50]}...'")

            # Gera embedding
            content = CompanyKnowledgeBase.format_content(question, answer, category)
            embedding = await openai_service.get_embedding(content)

            # Cria documento
            document = CompanyKnowledgeBase.create_document(
                company_id=company_id,
                question=question,
                answer=answer,
                category=category,
                priority=priority,
                embedding=embedding,
            )

            # Insere no MongoDB
            db = mongodb.get_database()
            collection = db[self.collection_name]
            result = await collection.insert_one(document)

            # Limpa cache relacionado
            self._invalidate_cache(company_id)

            logger.info(f"[RAG] ✅ FAQ criada: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"[RAG] ❌ Erro ao criar knowledge: {e}", exc_info=True)
            raise

    async def update_knowledge(
        self,
        entry_id: str,
        company_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> bool:
        """
        Atualiza entrada existente

        Returns:
            True se atualizado com sucesso
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            # Busca documento atual
            current = await collection.find_one(
                {"_id": ObjectId(entry_id), "company_id": company_id}
            )

            if not current:
                return False

            update_doc = {}
            regenerate_embedding = False

            # Verifica se precisa regenerar embedding
            if question or answer or category:
                regenerate_embedding = True

                new_question = question or current["metadata"]["question"]
                new_answer = answer or current["metadata"]["answer"]
                new_category = category or current["metadata"]["category"]

                # Gera novo embedding
                content = CompanyKnowledgeBase.format_content(
                    new_question, new_answer, new_category
                )
                embedding = await openai_service.get_embedding(content)

                update_doc["content"] = content
                update_doc["embedding"] = embedding
                update_doc["metadata.question"] = new_question
                update_doc["metadata.answer"] = new_answer
                update_doc["metadata.category"] = new_category
                update_doc["metadata.keywords"] = CompanyKnowledgeBase.extract_keywords(
                    new_question, new_answer
                )

            if priority is not None:
                update_doc["metadata.priority"] = priority

            from datetime import datetime

            update_doc["metadata.updated_at"] = datetime.utcnow()

            # Atualiza no MongoDB
            result = await collection.update_one(
                {"_id": ObjectId(entry_id), "company_id": company_id},
                {"$set": update_doc},
            )

            # Limpa cache
            self._invalidate_cache(company_id)

            logger.info(
                f"FAQ atualizada: {entry_id} (embedding regenerado: {regenerate_embedding})"
            )
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Erro ao atualizar knowledge: {e}")
            raise

    async def delete_knowledge(self, entry_id: str, company_id: str) -> bool:
        """
        Soft delete de entrada

        Returns:
            True se deletado com sucesso
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            from datetime import datetime

            result = await collection.update_one(
                {"_id": ObjectId(entry_id), "company_id": company_id},
                {
                    "$set": {
                        "is_active": False,
                        "metadata.updated_at": datetime.utcnow(),
                    }
                },
            )

            # Limpa cache
            self._invalidate_cache(company_id)

            logger.info(f"FAQ deletada (soft): {entry_id}")
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Erro ao deletar knowledge: {e}")
            raise

    async def list_knowledge(
        self,
        company_id: str,
        category: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Lista entradas do knowledge base

        Returns:
            Dict com total e lista de entries
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            query = {"company_id": company_id, "is_active": True}
            if category:
                query["metadata.category"] = category

            # Total
            total = await collection.count_documents(query)

            # Documentos (sem embedding para economizar banda)
            cursor = (
                collection.find(
                    query,
                    {
                        "_id": 1,
                        "metadata.question": 1,
                        "metadata.answer": 1,
                        "metadata.category": 1,
                        "metadata.priority": 1,
                        "created_at": 1,
                        "metadata.updated_at": 1,
                    },
                )
                .skip(skip)
                .limit(limit)
            )

            docs = await cursor.to_list(length=limit)

            entries = [
                {
                    "id": str(doc["_id"]),
                    "question": doc["metadata"]["question"],
                    "answer": doc["metadata"]["answer"],
                    "category": doc["metadata"]["category"],
                    "priority": doc["metadata"]["priority"],
                    "created_at": doc["created_at"].isoformat(),
                    "updated_at": doc["metadata"]["updated_at"].isoformat(),
                }
                for doc in docs
            ]

            return {"total": total, "entries": entries}

        except Exception as e:
            logger.error(f"Erro ao listar knowledge: {e}")
            raise

    async def bulk_create(
        self, company_id: str, entries: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Criação em massa de FAQs

        Args:
            company_id: ID da empresa
            entries: Lista de dicts com question, answer, category, priority

        Returns:
            Lista de IDs criados
        """
        try:
            logger.info(f"[RAG] Bulk create: {len(entries)} FAQs")

            # Prepara textos para batch embedding
            texts = [
                CompanyKnowledgeBase.format_content(
                    e["question"], e["answer"], e["category"]
                )
                for e in entries
            ]

            # Gera embeddings em batch
            embeddings = await openai_service.batch_embeddings(texts)

            # Cria documentos
            documents = [
                CompanyKnowledgeBase.create_document(
                    company_id=company_id,
                    question=entries[i]["question"],
                    answer=entries[i]["answer"],
                    category=entries[i]["category"],
                    priority=entries[i].get("priority", 3),
                    embedding=embeddings[i],
                )
                for i in range(len(entries))
            ]

            # Insere em massa
            db = mongodb.get_database()
            collection = db[self.collection_name]
            result = await collection.insert_many(documents)

            # Limpa cache
            self._invalidate_cache(company_id)

            ids = [str(id) for id in result.inserted_ids]
            logger.info(f"[RAG] ✅ Bulk create: {len(ids)} FAQs criadas com sucesso")
            return ids

        except Exception as e:
            logger.error(f"[RAG] ❌ Erro no bulk create: {e}", exc_info=True)
            raise

    def _invalidate_cache(self, company_id: str):
        """Limpa cache relacionado a uma empresa"""
        logger.debug(f"[RAG] Cache invalidado para company {company_id}")


# Instância global
rag_service = RAGService()
