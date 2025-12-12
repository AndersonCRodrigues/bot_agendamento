from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from ..config import settings


class ChatSession:
    collection_name = "chat_sessions"

    @staticmethod
    def create_new_session(
        session_id: str, company_id: str, customer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            "paused_until": None,
            "last_sender_type": "user",
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
        }

    @staticmethod
    def create_message(
        role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
        }

    @staticmethod
    def create_rag_usage(
        question: str,
        relevance_score: float,
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "relevance_score": relevance_score,
            "used_at": datetime.now(),
        }

    @staticmethod
    def get_indexes():
        return [
            [("session_id", 1)],
            [("company_id", 1), ("updated_at", -1)],
            [("expires_at", 1)],
        ]

    @staticmethod
    def get_ttl_index():
        return {"keys": [("expires_at", 1)], "expireAfterSeconds": 0}
