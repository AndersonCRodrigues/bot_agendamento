import logging
from ..state import GraphState
from ...models import ChatResponse, Directives, KanbanStatus

logger = logging.getLogger(__name__)


async def process_directives_node(state: GraphState) -> GraphState:
    try:
        raw = state.get("llm_response_raw", {})

        directives_data = raw.get("directives", {"type": "normal"})
        directives_type = directives_data.get("type", "normal")
        kanban_status = raw.get("kanban_status", KanbanStatus.EM_ATENDIMENTO)

        logger.info(
            f"[PROCESS] Processando diretiva: type={directives_type}, kanban={kanban_status}"
        )

        if directives_type == "appointment_confirmation":
            directives_data = _validate_and_enrich_appointment(directives_data, state)
            directives_type = directives_data.get("type", "normal")

            if directives_type == "appointment_confirmation":
                logger.info("[PROCESS] ✅ Agendamento validado com sucesso")
            else:
                logger.warning(
                    "[PROCESS] ⚠️ Agendamento falhou na validação, revertido para 'normal'"
                )

        elif kanban_status == KanbanStatus.AGENDADO and directives_type == "normal":
            logger.warning(
                "[PROCESS] ⚠️ INCONSISTÊNCIA DETECTADA: "
                "kanban_status='Agendado' mas directive_type='normal'. "
                "Tentando construir appointment_confirmation..."
            )

            entities = state.get("extracted_entities", {})
            filtered_agenda = state.get("filtered_agenda")

            if filtered_agenda and filtered_agenda.options:
                first_option = filtered_agenda.options[0]

                potential_appointment = {
                    "profissional_id": first_option.get("professional_id"),
                    "servico_id": filtered_agenda.service_id,
                    "data": first_option.get("date"),
                    "hora": (
                        first_option.get("slots", [None])[0]
                        if first_option.get("slots")
                        else None
                    ),
                }

                logger.info(
                    f"[PROCESS] Tentando construir appointment com: {potential_appointment}"
                )

                if all(potential_appointment.values()):
                    directives_data["type"] = "appointment_confirmation"
                    directives_data["payload_appointment"] = potential_appointment

                    directives_data = _validate_and_enrich_appointment(
                        directives_data, state
                    )
                    directives_type = directives_data.get("type")

                    if directives_type == "appointment_confirmation":
                        logger.info("[PROCESS] ✅ Agendamento reconstruído com sucesso")
                    else:
                        logger.error("[PROCESS] ❌ Falha ao reconstruir agendamento")
                else:
                    logger.error(
                        f"[PROCESS] ❌ Dados incompletos para reconstruir agendamento: {potential_appointment}"
                    )
            else:
                logger.error(
                    "[PROCESS] ❌ Sem agenda filtrada para reconstruir agendamento"
                )

        if directives_type != "appointment_confirmation":
            directives_data.pop("payload_appointment", None)

        directives = Directives(**directives_data)

        final_response = ChatResponse(
            cliente_id=state["session_id"],
            company_id=state["company_id"],
            response_text=raw.get("response_text", "Erro interno. Tente novamente."),
            kanban_status=kanban_status,
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

        logger.info(
            f"[PROCESS] Resposta final: directive={directives.type}, "
            f"kanban={final_response.kanban_status}"
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

    def revert_to_normal(reason: str):
        logger.warning(f"[VALIDATE_APPOINTMENT] Revertendo para normal: {reason}")
        directives_data["type"] = "normal"
        directives_data.pop("payload_appointment", None)
        return directives_data

    if not payload:
        return revert_to_normal("payload_appointment vazio")

    profissional_id = payload.get("profissional_id")
    servico_id = payload.get("servico_id")
    data = payload.get("data")
    hora = payload.get("hora")

    logger.info(
        f"[VALIDATE_APPOINTMENT] Validando: prof={profissional_id}, "
        f"serv={servico_id}, data={data}, hora={hora}"
    )

    if not all([profissional_id, servico_id, data, hora]):
        missing = []
        if not profissional_id:
            missing.append("profissional_id")
        if not servico_id:
            missing.append("servico_id")
        if not data:
            missing.append("data")
        if not hora:
            missing.append("hora")
        return revert_to_normal(f"Campos faltando: {', '.join(missing)}")

    full_agenda = state.get("full_agenda")

    if not full_agenda:
        return revert_to_normal("Agenda não carregada no state")

    prof_info = full_agenda.professionals.get(profissional_id)
    service_info = full_agenda.services.get(servico_id)

    if not prof_info:
        return revert_to_normal(
            f"Profissional {profissional_id} não encontrado na agenda"
        )

    if not service_info:
        return revert_to_normal(f"Serviço {servico_id} não encontrado na agenda")

    if servico_id not in prof_info.services:
        return revert_to_normal(
            f"Profissional {profissional_id} não oferece serviço {servico_id}"
        )

    availability = full_agenda.availability.get(profissional_id, {}).get(servico_id, {})
    date_slots = availability.get(data, [])

    if hora not in date_slots:
        return revert_to_normal(
            f"Horário {hora} não disponível para prof={profissional_id}, "
            f"serv={servico_id}, data={data}. Slots disponíveis: {date_slots}"
        )

    payload["profissional_name"] = prof_info.name
    payload["servico_name"] = service_info.name

    directives_data["payload_appointment"] = payload

    logger.info(
        f"[VALIDATE_APPOINTMENT] ✅ Agendamento validado: "
        f"{prof_info.name} - {service_info.name} em {data} às {hora}"
    )

    return directives_data
