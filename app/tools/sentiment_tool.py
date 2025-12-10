import re
import hashlib
import json
from typing import List, Dict, Optional
import logging
from ..models import SentimentAnalysisResult, Sentiment
from ..services import openai_service
from ..database import cache
from ..config import settings

logger = logging.getLogger(__name__)


SENTIMENT_SYSTEM_PROMPT = """
Você é especialista em análise de sentimento para atendimento de agendamento.

Classifique o sentimento em UMA categoria:
- positivo: Cliente satisfeito, cooperativo, animado
- neutro: Cliente neutro, apenas informativo
- negativo: Cliente insatisfeito mas controlado
- raiva: Cliente irritado, agressivo
- ansioso: Cliente preocupado, urgente
- confuso: Cliente perdido, não entende
- triste: Cliente em dificuldade emocional

Retorne JSON:
{
  "sentiment": "<categoria>",
  "score": <0-100, intensidade>,
  "confidence": "baixa" | "média" | "alta"
}

Considere o contexto histórico para avaliar evolução emocional.
"""


class SentimentTool:
    """Tool de análise de sentimento"""

    def __init__(self):
        self.cache_ttl = 3600

    async def analyze(
        self, message: str, recent_history: List[Dict[str, str]]
    ) -> SentimentAnalysisResult:
        try:
            cache_key = self._get_cache_key(message, recent_history)
            cached = cache.get(cache_key)
            if cached:
                logger.debug("Sentiment cache hit")
                return SentimentAnalysisResult(**cached)

            quick_result = self._quick_classify(message)
            if quick_result:
                logger.debug("Sentiment via heurística")
                cache.set(cache_key, quick_result.model_dump(), self.cache_ttl)
                return quick_result

            result = await self._call_llm(message, recent_history)
            cache.set(cache_key, result.model_dump(), self.cache_ttl)

            logger.debug(f"Sentiment via LLM: {result.sentiment}")
            return result

        except Exception as e:
            logger.error(f"Erro na análise de sentimento: {e}")
            return SentimentAnalysisResult(
                sentiment=Sentiment.NEUTRO, score=50, confidence="baixa"
            )

    def _quick_classify(self, message: str) -> Optional[SentimentAnalysisResult]:
        """Classificação rápida via regex patterns"""
        message_lower = message.lower()

        raiva_patterns = [
            r"\b(absurdo|ridículo|inadmissível|vergonha|palhaçada)\b",
            r"\b(não aguento|estou farto|chega|basta)\b",
            r"[!]{2,}",
        ]
        if any(re.search(p, message_lower) for p in raiva_patterns):
            return SentimentAnalysisResult(
                sentiment=Sentiment.RAIVA, score=85, confidence="alta"
            )

        positivo_patterns = [
            r"\b(obrigad[oa]|agradeço|perfeito|ótimo|excelente|maravilhoso)\b",
            r"\b(pode marcar|confirmo|fechado|topo|combinado)\b",
        ]
        if any(re.search(p, message_lower) for p in positivo_patterns):
            return SentimentAnalysisResult(
                sentiment=Sentiment.POSITIVO, score=80, confidence="alta"
            )

        ansioso_patterns = [
            r"\b(urgente|rápido|agora|hoje mesmo|preciso)\b",
            r"\b(não posso esperar|é para já)\b",
        ]
        if any(re.search(p, message_lower) for p in ansioso_patterns):
            return SentimentAnalysisResult(
                sentiment=Sentiment.ANSIOSO, score=75, confidence="média"
            )

        confuso_patterns = [
            r"\b(não entend[io]|como assim|o que é)\b",
            r"\b(explica|dúvida|confus[oa])\b",
            r"\?{2,}",
        ]
        if any(re.search(p, message_lower) for p in confuso_patterns):
            return SentimentAnalysisResult(
                sentiment=Sentiment.CONFUSO, score=70, confidence="média"
            )

        triste_patterns = [
            r"\b(difícil|complicad[oa]|não consigo)\b",
            r"\b(problema|situação difícil)\b",
        ]
        if any(re.search(p, message_lower) for p in triste_patterns):
            return SentimentAnalysisResult(
                sentiment=Sentiment.TRISTE, score=70, confidence="média"
            )

        return None

    async def _call_llm(
        self, message: str, recent_history: List[Dict[str, str]]
    ) -> SentimentAnalysisResult:
        """Chamada LLM para casos ambíguos"""

        history_text = self._format_history(recent_history)

        prompt = f"""Analise o sentimento da seguinte mensagem do cliente:

HISTÓRICO RECENTE:
{history_text}

MENSAGEM ATUAL:
"{message}"

Retorne APENAS o JSON com o resultado da análise."""

        messages = [
            {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await openai_service.chat_completion(
            messages=messages,
            model=settings.TOOL_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result_dict = json.loads(response["content"])
        return SentimentAnalysisResult(**result_dict)

    def _format_history(self, recent_history: List[Dict[str, str]]) -> str:
        """Formata histórico para o prompt"""
        if not recent_history:
            return "(Sem histórico anterior)"

        formatted = []
        for msg in recent_history[-4:]:
            role = "Cliente" if msg["role"] == "user" else "Agente"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    def _get_cache_key(self, message: str, recent_history: List[Dict[str, str]]) -> str:
        """Gera chave de cache única"""
        context = message
        if recent_history:
            context += "".join([m["content"] for m in recent_history[-2:]])

        hash_obj = hashlib.md5(context.encode())
        return f"sentiment:{hash_obj.hexdigest()}"


sentiment_tool = SentimentTool()
