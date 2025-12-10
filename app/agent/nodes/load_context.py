import logging
from datetime import datetime
from ..state import GraphState
from ...models.scheduling import FullAgenda

logger = logging.getLogger(__name__)


async def load_context_node(state: GraphState) -> GraphState:
    """
    Carrega agenda completa no STATE (não no prompt do LLM).

    IMPORTANTE: A agenda fica em memória no grafo,
    não será enviada ao LLM em cada turno.
    """
    try:
        logger.info(f"[LOAD_CONTEXT] Iniciando sessão {state['session_id']}")

        full_agenda = FullAgenda(**state["company_agenda"])

        logger.info(
            f"[LOAD_CONTEXT] Agenda carregada: "
            f"{len(full_agenda.professionals)} profissionais, "
            f"{len(full_agenda.services)} serviços"
        )

        return {
            **state,
            "full_agenda": full_agenda,
            "filtered_agenda": None,
        }

    except Exception as e:
        logger.error(f"[LOAD_CONTEXT] Erro: {e}", exc_info=True)
        return {**state, "error": str(e)}
