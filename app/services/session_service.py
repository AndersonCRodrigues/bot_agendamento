from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date
from ..database import mongodb
from ..schemas import ChatSession

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self):
        self.collection_name = ChatSession.collection_name

    def _convert_dates_to_datetime(self, obj: Any) -> Any:
        if isinstance(obj, date) and not isinstance(obj, datetime):
            converted = datetime.combine(obj, datetime.min.time())
            logger.warning(
                f"Convertendo date para datetime: {obj} -> {converted}. "
                f"Considere enviar datetime diretamente."
            )
            return converted
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
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            customer_context = self._convert_dates_to_datetime(customer_context)

            session = await collection.find_one({"session_id": session_id})

            if session:
                logger.debug(f"Sessao existente recuperada: {session_id}")
                await collection.update_one(
                    {"session_id": session_id},
                    {
                        "$set": {
                            "customer_context": customer_context,
                            "updated_at": datetime.now(),
                        }
                    },
                )
                session["customer_context"] = customer_context
                return session

            new_session = ChatSession.create_new_session(
                session_id=session_id,
                company_id=company_id,
                customer_context=customer_context,
            )

            new_session = self._convert_dates_to_datetime(new_session)

            await collection.insert_one(new_session)
            logger.info(f"Nova sessao criada: {session_id}")

            return new_session

        except Exception as e:
            logger.error(f"Erro ao obter/criar sessao: {e}", exc_info=True)
            raise

    async def append_messages(self, session_id: str, messages: List[Dict[str, Any]]):
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            messages = self._convert_dates_to_datetime(messages)

            await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": {"$each": messages}},
                    "$set": {"updated_at": datetime.now()},
                    "$inc": {"summary.total_interactions": 1},
                },
            )

            logger.debug(f"Mensagens adicionadas a sessao {session_id}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagens: {e}", exc_info=True)
            raise

    async def get_recent_history(
        self, session_id: str, n: int = 4
    ) -> List[Dict[str, Any]]:
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
            logger.error(f"Erro ao obter historico recente: {e}", exc_info=True)
            return []

    async def update_summary(
        self,
        session_id: str,
        sentiment: Optional[str] = None,
        intent: Optional[str] = None,
        kanban_status: Optional[str] = None,
        rag_hit: bool = False,
    ):
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            update_ops = {"$set": {"updated_at": datetime.now()}}

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

            logger.debug(f"Summary atualizado para sessao {session_id}")

        except Exception as e:
            logger.error(f"Erro ao atualizar summary: {e}", exc_info=True)

    async def add_rag_usage(
        self, session_id: str, question: str, relevance_score: float
    ):
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            rag_usage = ChatSession.create_rag_usage(question, relevance_score)

            await collection.update_one(
                {"session_id": session_id}, {"$push": {"rag_context_used": rag_usage}}
            )

        except Exception as e:
            logger.error(f"Erro ao registrar uso do RAG: {e}", exc_info=True)

    async def delete_session(self, session_id: str) -> bool:
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            result = await collection.delete_one({"session_id": session_id})

            if result.deleted_count > 0:
                logger.info(f"Sessao deletada: {session_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Erro ao deletar sessao: {e}", exc_info=True)
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = mongodb.get_database()
            collection = db[self.collection_name]

            session = await collection.find_one({"session_id": session_id})
            return session

        except Exception as e:
            logger.error(f"Erro ao buscar sessao: {e}", exc_info=True)
            return None


session_service = SessionService()
