import logging
from ..state import GraphState
from ...services import session_service
from ...schemas import ChatSession

logger = logging.getLogger(__name__)


async def save_session_node(state: GraphState) -> GraphState:
    try:
        response = state.get("final_response")

        if not response:
            return state

        def get_value(obj):
            return obj.value if hasattr(obj, "value") else obj

        user_message = ChatSession.create_message(
            role="user",
            content=state["user_message"],
            metadata={
                "sentiment": (
                    get_value(state["sentiment_result"].sentiment)
                    if state.get("sentiment_result")
                    else None
                ),
                "intent": (
                    get_value(state["intent_result"].intent)
                    if state.get("intent_result")
                    else None
                ),
            },
        )

        assistant_message = ChatSession.create_message(
            role="assistant",
            content=response.response_text,
            metadata={
                "kanban_status": get_value(response.kanban_status),
                "directive_type": response.directives.type,
            },
        )

        await session_service.append_messages(
            session_id=state["session_id"], messages=[user_message, assistant_message]
        )

        await session_service.update_summary(
            session_id=state["session_id"],
            sentiment=(
                get_value(state["sentiment_result"].sentiment)
                if state.get("sentiment_result")
                else None
            ),
            intent=(
                get_value(state["intent_result"].intent)
                if state.get("intent_result")
                else None
            ),
            kanban_status=get_value(response.kanban_status),
            rag_hit=False,
        )

        return state

    except Exception as e:
        logger.error(f"[SAVE_SESSION] Erro: {e}", exc_info=True)
        return {**state, "error": f"Erro save session: {e}"}
