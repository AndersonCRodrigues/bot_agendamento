from datetime import datetime
from typing import List, Dict, Any


class CompanyKnowledgeBase:
    """
    Schema para a collection company_knowledge_base no MongoDB

    Estrutura:
    {
        "_id": ObjectId,
        "company_id": str,
        "content": str (formatado: "Pergunta: X\nResposta: Y\nCategoria: Z"),
        "embedding": List[float] (512 dimensões),
        "metadata": {
            "question": str,
            "answer": str,
            "category": str,
            "priority": int (1-5),
            "keywords": List[str],
            "updated_at": datetime
        },
        "is_active": bool,
        "created_at": datetime
    }
    """

    collection_name = "company_knowledge_base"

    @staticmethod
    def format_content(question: str, answer: str, category: str) -> str:
        """Formata conteúdo para gerar embedding"""
        return f"Pergunta: {question}\nResposta: {answer}\nCategoria: {category}"

    @staticmethod
    def extract_keywords(question: str, answer: str) -> List[str]:
        """Extrai keywords simples do texto (para busca híbrida)"""
        import re

        text = f"{question} {answer}".lower()
        # Remove pontuação e pega palavras > 3 caracteres
        words = re.findall(r"\b\w{4,}\b", text)
        # Remove duplicatas mantendo ordem
        seen = set()
        keywords = []
        for word in words:
            if word not in seen:
                seen.add(word)
                keywords.append(word)
        return keywords[:20]  # Máximo 20 keywords

    @staticmethod
    def create_document(
        company_id: str,
        question: str,
        answer: str,
        category: str,
        priority: int,
        embedding: List[float],
    ) -> Dict[str, Any]:
        """Cria documento completo para inserir no MongoDB"""
        now = datetime.now()
        content = CompanyKnowledgeBase.format_content(question, answer, category)
        keywords = CompanyKnowledgeBase.extract_keywords(question, answer)

        return {
            "company_id": company_id,
            "content": content,
            "embedding": embedding,
            "metadata": {
                "question": question,
                "answer": answer,
                "category": category,
                "priority": priority,
                "keywords": keywords,
                "updated_at": now,
            },
            "is_active": True,
            "created_at": now,
        }

    @staticmethod
    def get_indexes():
        """Define índices necessários para a collection"""
        return [
            # Índice composto para filtros comuns
            [("company_id", 1), ("is_active", 1)],
            # Índice para categoria
            [("company_id", 1), ("metadata.category", 1)],
            # Índice de texto para keywords
            [("metadata.keywords", "text")],
        ]
