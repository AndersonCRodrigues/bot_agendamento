import logging
import json
from ..state import GraphState
from ..prompts import build_dynamic_prompt
from ...services import openai_service
from ...models import ChatResponse, Directives

logger = logging.getLogger(__name__)


async def agent_respond_node(state: GraphState) -> GraphState:
    try:
        logger.info("[RESPOND] Gerando resposta do agente")

        # 1. Constrói o Prompt Dinâmico
        # Usa o 'rag_formatted' que agora contém a AGENDA
        system_prompt = build_dynamic_prompt(
            config=state["company_config"],
            customer_context=_get_customer_str(state["customer_profile"]),
            agenda_context=state["rag_formatted"],
            is_data_complete=state["is_data_complete"],
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Histórico Recente
        for msg in state["recent_history"]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Mensagem Atual
        messages.append({"role": "user", "content": state["user_message"]})

        # 2. Chamada OpenAI (JSON Mode)
        response = await openai_service.chat_completion(
            messages=messages,
            temperature=0.2,  # Baixa temperatura para seguir regras
            response_format={"type": "json_object"},
        )

        # 3. Parse e Validação
        content = response["content"]
        try:
            response_dict = json.loads(content)

            # Garante que a estrutura bate com o ChatResponse esperado pelo Backend
            # Aqui criamos apenas a parte 'interna' da resposta
            # O objeto ChatResponse completo é montado no final (Main ou Process Decision)
            # Mas vamos salvar no state como um dict por enquanto

            # Validação básica de chaves
            if "directives" not in response_dict:
                raise ValueError("JSON sem campo 'directives'")

        except json.JSONDecodeError:
            logger.error(f"[RESPOND] Erro JSON do LLM: {content}")
            raise

        return {
            **state,
            "llm_response_raw": response_dict,  # Guardamos o dict puro para processar depois
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
        }

    except Exception as e:
        logger.error(f"[RESPOND] Erro crítico: {e}", exc_info=True)
        return {**state, "error": str(e)}


def _get_customer_str(profile) -> str:
    # Helper simples para reformatar se necessário
    return f"Nome: {profile.nome}, Email: {profile.email}, Tel: {profile.telefone}"
