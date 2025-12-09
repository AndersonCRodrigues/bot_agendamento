import logging
from ..state import GraphState
from ...models import ChatResponse, Directives, KanbanStatus

logger = logging.getLogger(__name__)


async def process_directives_node(state: GraphState) -> GraphState:
    """
    Nó Final: Monta o objeto ChatResponse estruturado.
    """
    try:
        raw = state.get("llm_response_raw", {})

        # 1. Extrai Diretivas
        directives_data = raw.get("directives", {"type": "normal"})
        directives = Directives(**directives_data)

        # 2. Extrai Status Kanban
        k_status = raw.get("kanban_status", KanbanStatus.EM_ATENDIMENTO)

        # 3. Monta Resposta Final
        final_response = ChatResponse(
            cliente_id=state["session_id"],  # Usando session_id como ID do cliente
            company_id=state["company_id"],
            response_text=raw.get("response_text", "Erro interno. Tente novamente."),
            kanban_status=k_status,
            directives=directives,
            metadata={
                "intent": (
                    state["intent_result"].intent
                    if state.get("intent_result")
                    else "UNKNOWN"
                ),
                "tokens": state.get("prompt_tokens", 0)
                + state.get("completion_tokens", 0),
            },
        )

        logger.info(
            f"[PROCESS] Diretiva gerada: {directives.type} | Kanban: {k_status}"
        )

        return {**state, "final_response": final_response}

    except Exception as e:
        logger.error(f"[PROCESS] Erro ao processar diretivas: {e}", exc_info=True)
        return {**state, "error": str(e)}
