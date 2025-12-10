import logging
from datetime import datetime
from ..state import GraphState
from ...models.scheduling import FullAgenda
from ...services import session_service

logger = logging.getLogger(__name__)


async def load_context_node(state: GraphState) -> GraphState:
    try:
        logger.info(f"[LOAD_CONTEXT] Iniciando sessao {state['session_id']}")

        full_agenda = FullAgenda(**state["company_agenda"])

        logger.info(
            f"[LOAD_CONTEXT] Agenda carregada: "
            f"{len(full_agenda.professionals)} profissionais, "
            f"{len(full_agenda.services)} servicos"
        )

        session = await session_service.get_or_create_session(
            session_id=state["session_id"],
            company_id=state["company_id"],
            customer_context=state["customer_profile"],
        )

        recent_history = await session_service.get_recent_history(
            session_id=state["session_id"], n=4
        )

        recent_formatted = [
            {"role": msg["role"], "content": msg["content"]} for msg in recent_history
        ]

        logger.info(
            f"[LOAD_CONTEXT] Historico: {len(session.get('messages', []))} msgs, "
            f"Recente: {len(recent_formatted)} msgs"
        )

        return {
            **state,
            "full_agenda": full_agenda,
            "filtered_agenda": None,
            "chat_history": session.get("messages", []),
            "recent_history": recent_formatted,
        }

    except Exception as e:
        logger.error(f"[LOAD_CONTEXT] Erro: {e}", exc_info=True)
        return {**state, "error": str(e)}
