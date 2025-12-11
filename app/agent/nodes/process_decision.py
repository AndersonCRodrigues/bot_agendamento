import logging
from ..state import GraphState
from ...models import ChatResponse, Directives, KanbanStatus

logger = logging.getLogger(__name__)


async def process_directives_node(state: GraphState) -> GraphState:
    try:
        raw = state.get("llm_response_raw", {})

        directives_data = raw.get("directives", {"type": "normal"})
        directives_type = directives_data.get("type", "normal")

        if directives_type != "appointment_confirmation":
            directives_data.pop("payload_appointment", None)
        else:
            directives_data = _validate_and_enrich_appointment(directives_data, state)
            directives_type = directives_data.get("type", "normal")

        directives = Directives(**directives_data)

        k_status = raw.get("kanban_status", KanbanStatus.EM_ATENDIMENTO)

        final_response = ChatResponse(
            cliente_id=state["session_id"],
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
                "sentiment": (
                    state["sentiment_result"].sentiment
                    if state.get("sentiment_result")
                    else "NEUTRO"
                ),
                "tokens": state.get("prompt_tokens", 0)
                + state.get("completion_tokens", 0),
            },
        )

        return {**state, "final_response": final_response}

    except Exception as e:
        logger.error(f"[PROCESS] Erro: {e}", exc_info=True)

        fallback_response = ChatResponse(
            cliente_id=state["session_id"],
            company_id=state["company_id"],
            response_text="Desculpe, tive um erro técnico. Pode repetir?",
            kanban_status=KanbanStatus.EM_ATENDIMENTO,
            directives=Directives(type="normal"),
            metadata={"error": str(e)},
        )
        return {**state, "final_response": fallback_response, "error": str(e)}


def _validate_and_enrich_appointment(directives_data: dict, state: GraphState) -> dict:
    payload = directives_data.get("payload_appointment", {})

    def revert_to_normal():
        directives_data["type"] = "normal"
        directives_data.pop("payload_appointment", None)
        return directives_data

    if not payload:
        return revert_to_normal()

    profissional_id = payload.get("profissional_id")
    servico_id = payload.get("servico_id")
    data = payload.get("data")
    hora = payload.get("hora")

    if not all([profissional_id, servico_id, data, hora]):
        return revert_to_normal()

    full_agenda = state.get("full_agenda")

    if not full_agenda:
        return revert_to_normal()

    prof_info = full_agenda.professionals.get(profissional_id)
    service_info = full_agenda.services.get(servico_id)

    if not prof_info or not service_info:
        return revert_to_normal()

    if servico_id not in prof_info.services:
        return revert_to_normal()

    availability = full_agenda.availability.get(profissional_id, {}).get(servico_id, {})
    date_slots = availability.get(data, [])

    if hora not in date_slots:
        return revert_to_normal()

    payload["profissional_name"] = prof_info.name
    payload["servico_name"] = service_info.name

    directives_data["payload_appointment"] = payload

    return directives_data
