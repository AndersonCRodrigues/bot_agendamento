import logging
from ..state import GraphState
from ...models import ChatResponse, Directives, KanbanStatus

logger = logging.getLogger(__name__)


async def process_directives_node(state: GraphState) -> GraphState:

    try:
        raw = state.get("llm_response_raw", {})

        directives_data = raw.get("directives", {"type": "normal"})
        directives_type = directives_data.get("type", "normal")

        if directives_type == "appointment_confirmation":
            directives_data = _validate_and_enrich_appointment(directives_data, state)

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

        logger.info(f"[PROCESS] Diretiva: {directives.type} | Kanban: {k_status}")

        if directives_type == "appointment_confirmation":
            logger.info(
                f"[PROCESS] Agendamento confirmado: "
                f"Prof={directives.payload_appointment.profissional_id}, "
                f"Serv={directives.payload_appointment.servico_id}, "
                f"Data={directives.payload_appointment.data}, "
                f"Hora={directives.payload_appointment.hora}"
            )

        return {**state, "final_response": final_response}

    except Exception as e:
        logger.error(f"[PROCESS] Erro ao processar diretivas: {e}", exc_info=True)
        return {**state, "error": str(e)}


def _validate_and_enrich_appointment(directives_data: dict, state: GraphState) -> dict:

    payload = directives_data.get("payload_appointment", {})

    if not payload:
        logger.warning("[PROCESS] Appointment sem payload, mantendo como está")
        return directives_data

    profissional_id = payload.get("profissional_id")
    servico_id = payload.get("servico_id")
    data = payload.get("data")
    hora = payload.get("hora")

    missing = []
    if not profissional_id:
        missing.append("profissional_id")
    if not servico_id:
        missing.append("servico_id")
    if not data:
        missing.append("data")
    if not hora:
        missing.append("hora")

    if missing:
        logger.error(
            f"[PROCESS] Campos obrigatórios faltando: {missing}. " f"Payload: {payload}"
        )
        directives_data["type"] = "normal"
        return directives_data

    full_agenda = state.get("full_agenda")

    if full_agenda:
        prof_info = full_agenda.professionals.get(profissional_id)
        service_info = full_agenda.services.get(servico_id)

        payload["profissional_name"] = prof_info.name if prof_info else None
        payload["servico_name"] = service_info.name if service_info else None

    directives_data["payload_appointment"] = payload

    return directives_data
