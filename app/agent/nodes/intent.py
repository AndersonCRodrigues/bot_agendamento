import logging
from ..state import GraphState
from ...tools import intent_tool
from ...models import IntentAnalysisResult, Intent

logger = logging.getLogger(__name__)


async def analyze_intent_node(state: GraphState) -> GraphState:
    """
    Nó 3: Análise de intenção de pagamento (TOOL 2)
    Executa SEMPRE - não é condicional
    Usa patterns + LLM para classificar intenção
    """
    try:
        logger.info("[INTENT] Analisando intenção de pagamento")

        # Chama a tool
        result = await intent_tool.analyze(
            message=state["user_message"],
            recent_history=state["recent_history"],
            # CORREÇÃO 1: Use 'customer_profile' que é a chave correta no GraphState
            customer_context=state["customer_profile"],
        )

        logger.info(f"[INTENT] Resultado: {result.intent} - {result.reason}")

        # Atualiza estado
        return {
            **state,
            "intent_result": result,
            "intent_analyzed": True,
            "tools_called": ["intent"],
        }

    except Exception as e:
        logger.error(f"[INTENT] Erro: {e}", exc_info=True)

        return {
            **state,
            "intent_result": IntentAnalysisResult(
                intent=Intent.INFO, reason="Erro na análise (fallback)"
            ),
            "intent_analyzed": True,
            "tools_called": ["intent"],
            "error": f"Erro intent: {e}",
        }
