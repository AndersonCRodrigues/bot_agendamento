import logging
from ..state import GraphState
from ...services import session_service
from ...schemas import ChatSession

logger = logging.getLogger(__name__)


async def save_session_node(state: GraphState) -> GraphState:
    try:
        logger.info("[SAVE_SESSION] Salvando sessao")

        response = state["final_response"]

        def get_value(obj):
            return obj.value if hasattr(obj, "value") else obj

        user_message = ChatSession.create_message(
            role="user",
            content=state["user_message"],
            metadata={
                "sentiment": get_value(state["sentiment_result"].sentiment),
                "intent": get_value(state["intent_result"].intent),
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

        logger.debug(
            f"[SAVE_SESSION] Mensagens adicionadas a sessao {state['session_id']}"
        )

        await session_service.update_summary(
            session_id=state["session_id"],
            sentiment=get_value(state["sentiment_result"].sentiment),
            intent=get_value(state["intent_result"].intent),
            kanban_status=get_value(response.kanban_status),
            rag_hit=False,
        )

        logger.debug("[SAVE_SESSION] Summary atualizado")

        logger.info("[SAVE_SESSION] Sessao salva com sucesso")

        return state

    except Exception as e:
        logger.error(f"[SAVE_SESSION] Erro: {e}", exc_info=True)
        return {**state, "error": f"Erro save session: {e}"}
