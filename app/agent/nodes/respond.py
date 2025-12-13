import logging
import json
from ..state import GraphState
from ..prompts import build_optimized_prompt
from ...services import openai_service
from ...services.usage_service import usage_service
from ...tools.availability_tool import availability_tool

logger = logging.getLogger(__name__)


async def agent_respond_node(state: GraphState) -> GraphState:

    try:
        logger.info("[RESPOND] Gerando resposta do agente")

        agenda_context = _build_agenda_context(state)

        system_prompt = build_optimized_prompt(
            config=state["company_config"],
            customer_context=_format_customer_context(state["customer_profile"]),
            agenda_context=agenda_context,
            is_data_complete=state["is_data_complete"],
            intent=state["intent_result"].intent,
            sentiment=state["sentiment_result"].sentiment,
        )

        messages = [{"role": "system", "content": system_prompt}]

        for msg in state["recent_history"][-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": state["user_message"]})

        response = await openai_service.chat_completion(
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response["content"]
        try:
            response_dict = json.loads(content)

            if "directives" not in response_dict:
                raise ValueError("JSON sem campo 'directives'")

            if "response_text" not in response_dict:
                raise ValueError("JSON sem campo 'response_text'")

            if "kanban_status" not in response_dict:
                raise ValueError("JSON sem campo 'kanban_status'")

        except json.JSONDecodeError as e:
            logger.error(f"[RESPOND] Erro ao decodificar JSON: {content}")
            raise ValueError(f"LLM retornou JSON inválido: {str(e)}")

        prompt_tokens = response["usage"]["prompt_tokens"]
        completion_tokens = response["usage"]["completion_tokens"]

        await usage_service.track_usage(
            company_id=state["company_id"],
            session_id=state["session_id"],
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            model=response["model"],
            node_name="respond",
        )

        logger.info(
            f"[RESPOND] Tokens usados: {prompt_tokens} input + "
            f"{completion_tokens} output = {prompt_tokens + completion_tokens} total"
        )

        return {
            **state,
            "llm_response_raw": response_dict,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    except Exception as e:
        logger.error(f"[RESPOND] Erro crítico: {e}", exc_info=True)
        return {**state, "error": str(e)}


def _build_agenda_context(state: GraphState) -> str:

    intent = state["intent_result"].intent

    if intent not in ["SCHEDULING", "RESCHEDULE"]:
        full_agenda = state.get("full_agenda")
        if not full_agenda:
            return "AGENDA: Aguardando cliente definir interesse em agendamento."

        services_list = []
        for service_id, service_info in full_agenda.services.items():
            services_list.append(
                f"- {service_info.name}: R$ {service_info.price:.2f} ({service_info.duration}min)"
            )

        return (
            "SERVIÇOS DISPONÍVEIS:\n"
            + "\n".join(services_list)
            + "\n\nQuando o cliente demonstrar interesse em agendar, ofereça opções específicas de horários."
        )

    filtered = state.get("filtered_agenda")

    if not filtered or not filtered.options:
        return (
            "AGENDA: Cliente perguntou sobre agendamento mas não especificou "
            "serviço ou não há horários disponíveis. Pergunte qual serviço deseja "
            "ou confirme os dados primeiro."
        )

    return availability_tool.format_for_llm(filtered)


def _format_customer_context(profile) -> str:
    status = "COMPLETO" if profile.get("is_data_complete") else "INCOMPLETO"

    return (
        f"Nome: {profile.get('nome') or 'Não informado'} | "
        f"Email: {profile.get('email') or 'Não informado (OPCIONAL)'} | "
        f"Cadastro: {status}"
    )
