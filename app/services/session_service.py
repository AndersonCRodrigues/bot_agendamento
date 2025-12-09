from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date
from ..database import mongodb
from ..schemas import ChatSession

logger = logging.getLogger(__name__)


class SessionService:
    """Serviço de gestão de sessões de chat"""

    def __init__(self):
        self.collection_name = ChatSession.collection_name

    def _convert_dates_to_datetime(self, obj: Any) -> Any:
        """
        Converte recursivamente datetime.date para datetime.datetime
        MongoDB (BSON) não suporta datetime.date, apenas datetime.datetime

        Args:
            obj: Objeto a ser convertido (dict, list ou primitivo)

        Returns:
            Objeto com dates convertidos para datetime
        """
        if isinstance(obj, date) and not isinstance(obj, datetime):
            # Converte date para datetime (meia-noite)
            return datetime.combine(obj, datetime.min.time())
        elif isinstance(obj, dict):
            return {
                key: self._convert_dates_to_datetime(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._convert_dates_to_datetime(item) for item in obj]
        else:
            return obj

    async def get_or_create_session(
        self, session_id: str, company_id: str, customer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recupera sessão existente ou cria nova

        Args:
            session_id: ID da sessão (customer_id)
            company_id: ID da empresa
            customer_context: Contexto do cliente

        Returns:
            Documento da sessão
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            # Converte dates para datetime no customer_context
            customer_context = self._convert_dates_to_datetime(customer_context)

            # Tenta buscar sessão existente
            session = await collection.find_one({"session_id": session_id})

            if session:
                logger.debug(f"Sessão existente recuperada: {session_id}")
                # Atualiza customer_context (pode ter mudado)
                await collection.update_one(
                    {"session_id": session_id},
                    {
                        "$set": {
                            "customer_context": customer_context,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
                session["customer_context"] = customer_context
                return session

            # Cria nova sessão
            new_session = ChatSession.create_new_session(
                session_id=session_id,
                company_id=company_id,
                customer_context=customer_context,
            )

            # Garante que não há dates no documento
            new_session = self._convert_dates_to_datetime(new_session)

            await collection.insert_one(new_session)
            logger.info(f"Nova sessão criada: {session_id}")

            return new_session

        except Exception as e:
            logger.error(f"Erro ao obter/criar sessão: {e}")
            raise

    async def append_messages(self, session_id: str, messages: List[Dict[str, Any]]):
        """
        Adiciona mensagens ao histórico da sessão

        Args:
            session_id: ID da sessão
            messages: Lista de mensagens para adicionar
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            # Converte dates nas mensagens
            messages = self._convert_dates_to_datetime(messages)

            await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": {"$each": messages}},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"summary.total_interactions": 1},
                },
            )

            logger.debug(f"Mensagens adicionadas à sessão {session_id}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagens: {e}")
            raise

    async def get_recent_history(
        self, session_id: str, n: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Recupera últimas N mensagens da sessão

        Args:
            session_id: ID da sessão
            n: Número de mensagens (padrão: 4)

        Returns:
            Lista das últimas N mensagens
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            session = await collection.find_one(
                {"session_id": session_id}, {"messages": {"$slice": -n}}
            )

            if (
                session
                and "messages" in session
                and isinstance(session["messages"], list)
            ):
                return session["messages"]

            return []

        except Exception as e:
            logger.error(f"Erro ao obter histórico recente: {e}")
            return []

    async def update_summary(
        self,
        session_id: str,
        sentiment: Optional[str] = None,
        intent: Optional[str] = None,
        kanban_status: Optional[str] = None,
        rag_hit: bool = False,
    ):
        """
        Atualiza estatísticas da sessão

        Args:
            session_id: ID da sessão
            sentiment: Sentimento para adicionar ao histórico
            intent: Intenção para adicionar ao histórico
            kanban_status: Novo status do Kanban
            rag_hit: Se houve uso efetivo do RAG
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            update_ops = {"$set": {"updated_at": datetime.utcnow()}}

            # Consolida operações $push
            push_ops = {}
            if sentiment:
                push_ops["summary.sentiment_history"] = sentiment
            if intent:
                push_ops["summary.intent_history"] = intent

            if push_ops:
                update_ops["$push"] = push_ops

            if kanban_status:
                update_ops["$set"]["summary.last_kanban_status"] = kanban_status

            if rag_hit:
                update_ops["$inc"] = {"summary.rag_hits": 1}

            await collection.update_one({"session_id": session_id}, update_ops)

            logger.debug(f"Summary atualizado para sessão {session_id}")

        except Exception as e:
            logger.error(f"Erro ao atualizar summary: {e}")

    async def add_rag_usage(
        self, session_id: str, question: str, relevance_score: float
    ):
        """
        Registra uso de um item do RAG

        Args:
            session_id: ID da sessão
            question: Pergunta da FAQ usada
            relevance_score: Score de relevância
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            rag_usage = ChatSession.create_rag_usage(question, relevance_score)

            await collection.update_one(
                {"session_id": session_id}, {"$push": {"rag_context_used": rag_usage}}
            )

        except Exception as e:
            logger.error(f"Erro ao registrar uso do RAG: {e}")

    async def delete_session(self, session_id: str) -> bool:
        """
        Deleta uma sessão (reset)

        Args:
            session_id: ID da sessão

        Returns:
            True se deletado com sucesso
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            result = await collection.delete_one({"session_id": session_id})

            if result.deleted_count > 0:
                logger.info(f"Sessão deletada: {session_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Erro ao deletar sessão: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera sessão completa

        Args:
            session_id: ID da sessão

        Returns:
            Documento da sessão ou None
        """
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            session = await collection.find_one({"session_id": session_id})
            return session

        except Exception as e:
            logger.error(f"Erro ao buscar sessão: {e}")
            return None


# Instância global
session_service = SessionService()
