import logging
from ..state import GraphState
from ...tools import sentiment_tool

logger = logging.getLogger(__name__)


async def analyze_sentiment_node(state: GraphState) -> GraphState:
    """
    Nó 2: Análise de sentimento (TOOL 1)

    Executa SEMPRE - não é condicional
    Usa heurísticas + LLM para classificar sentimento
    """
    try:
        logger.info("[SENTIMENT] Analisando sentimento")

        # Chama a tool
        result = await sentiment_tool.analyze(
            message=state["user_message"], recent_history=state["recent_history"]
        )

        logger.info(
            f"[SENTIMENT] Resultado: {result.sentiment} "
            f"(score: {result.score}, confiança: {result.confidence})"
        )

        # Atualiza estado
        return {
            **state,
            "sentiment_result": result,
            "sentiment_analyzed": True,  # FLAG DE VALIDAÇÃO
            "tools_called": ["sentiment"],
        }

    except Exception as e:
        logger.error(f"[SENTIMENT] Erro: {e}", exc_info=True)
        # Fallback: sentimento neutro
        from ...models import SentimentAnalysisResult, Sentiment

        return {
            **state,
            "sentiment_result": SentimentAnalysisResult(
                sentiment=Sentiment.NEUTRO, score=50, confidence="baixa"
            ),
            "sentiment_analyzed": True,
            "tools_called": ["sentiment"],
            "error": f"Erro sentiment: {e}",
        }
