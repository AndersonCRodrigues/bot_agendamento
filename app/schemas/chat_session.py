from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from ..config import settings


class ChatSession:
    """
    Schema para a collection chat_sessions no MongoDB

    Estrutura:
    {
        "_id": ObjectId,
        "session_id": str (customer_id),
        "company_id": str,
        "messages": [
            {
                "role": "user" | "assistant" | "system",
                "content": str,
                "timestamp": datetime,
                "metadata": {
                    "sentiment": str,
                    "intent": str,
                    "tokens_used": int
                }
            }
        ],
        "rag_context_used": [
            {
                "question": str,
                "relevance_score": float,
                "used_at": datetime
            }
        ],
        "summary": {
            "total_interactions": int,
            "sentiment_history": List[str],
            "intent_history": List[str],
            "last_kanban_status": str,
            "rag_hits": int
        },
        "customer_context": dict,
        "created_at": datetime,
        "updated_at": datetime,
        "expires_at": datetime (TTL)
    }
    """

    collection_name = "chat_sessions"

    @staticmethod
    def create_new_session(
        session_id: str, company_id: str, customer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cria nova sessão"""
        now = datetime.now()
        expires_at = now + timedelta(days=settings.SESSION_TTL_DAYS)

        return {
            "session_id": session_id,
            "company_id": company_id,
            "messages": [],
            "rag_context_used": [],
            "summary": {
                "total_interactions": 0,
                "sentiment_history": [],
                "intent_history": [],
                "last_kanban_status": None,
                "rag_hits": 0,
            },
            "customer_context": customer_context,
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
        }

    @staticmethod
    def create_message(
        role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Cria estrutura de mensagem"""
        return {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
        }

    @staticmethod
    def create_rag_usage(question: str, relevance_score: float) -> Dict[str, Any]:
        """Registra uso de um item do RAG"""
        return {
            "question": question,
            "relevance_score": relevance_score,
            "used_at": datetime.now(),
        }

    @staticmethod
    def get_indexes():
        """Define índices necessários para a collection"""
        return [
            # Índice único para session_id
            [("session_id", 1)],
            # Índice composto para queries por empresa
            [("company_id", 1), ("updated_at", -1)],
            # TTL index para expiração automática
            [("expires_at", 1)],
        ]

    @staticmethod
    def get_ttl_index():
        """Retorna configuração do índice TTL"""
        return {"keys": [("expires_at", 1)], "expireAfterSeconds": 0}
