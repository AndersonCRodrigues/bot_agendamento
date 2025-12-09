import logging
from ..state import GraphState

logger = logging.getLogger(__name__)


async def validate_tools_node(state: GraphState) -> GraphState:
    """
    Nó 4: VALIDAÇÃO - Garante que tools foram executadas

    **CRÍTICO**: Previne o agente de "alucinar" que executou as tools
    quando na verdade não executou.

    Verifica:
    1. sentiment_analyzed = True
    2. intent_analyzed = True
    3. sentiment_result existe
    4. intent_result existe

    Se alguma validação falhar, PARA o fluxo com erro.
    """
    try:
        logger.info("[VALIDATE] Validando execução das tools")

        # Validações
        errors = []

        # 1. Verifica flag de sentiment
        if not state.get("sentiment_analyzed"):
            errors.append("ERRO: Sentiment analysis não foi executada")

        # 2. Verifica flag de intent
        if not state.get("intent_analyzed"):
            errors.append("ERRO: Intent analysis não foi executada")

        # 3. Verifica resultado de sentiment
        if not state.get("sentiment_result"):
            errors.append("ERRO: Resultado de sentiment não disponível")

        # 4. Verifica resultado de intent
        if not state.get("intent_result"):
            errors.append("ERRO: Resultado de intent não disponível")

        # 5. Verifica tools_called
        tools_called = state.get("tools_called", [])
        if "sentiment" not in tools_called:
            errors.append("ERRO: Tool 'sentiment' não foi chamada")

        if "intent" not in tools_called:
            errors.append("ERRO: Tool 'intent' não foi chamada")

        # Se há erros, registra e marca como inválido
        if errors:
            logger.error("[VALIDATE] ❌ VALIDAÇÃO FALHOU:")
            for error in errors:
                logger.error(f"  - {error}")

            return {**state, "tools_validated": False, "error": "; ".join(errors)}

        # ✅ VALIDAÇÃO OK
        logger.info("[VALIDATE] ✅ Tools validadas com sucesso")
        logger.info(f"  - Sentiment: {state['sentiment_result'].sentiment}")
        logger.info(f"  - Intent: {state['intent_result'].intent}")

        return {**state, "tools_validated": True}

    except Exception as e:
        logger.error(f"[VALIDATE] Erro na validação: {e}", exc_info=True)
        return {**state, "tools_validated": False, "error": f"Erro na validação: {e}"}
