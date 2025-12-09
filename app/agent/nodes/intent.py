import logging
from ..state import GraphState
from ...tools import intent_tool

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
            customer_context=state["customer_context"],
        )

        logger.info(f"[INTENT] Resultado: {result.intent} - {result.reason}")

        # Atualiza estado
        return {
            **state,
            "intent_result": result,
            "intent_analyzed": True,  # FLAG DE VALIDAÇÃO
            "tools_called": ["intent"],
        }

    except Exception as e:
        logger.error(f"[INTENT] Erro: {e}", exc_info=True)
        # Fallback: intenção neutra
        from ...models import IntentAnalysisResult, PaymentIntent

        return {
            **state,
            "intent_result": IntentAnalysisResult(
                intent=PaymentIntent.NEUTRA, reason="Erro na análise"
            ),
            "intent_analyzed": True,
            "tools_called": ["intent"],
            "error": f"Erro intent: {e}",
        }
