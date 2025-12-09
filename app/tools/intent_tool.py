import re
import hashlib
import json
from typing import List, Dict, Optional
import logging
from ..models import IntentAnalysisResult, Intent
from ..services import openai_service
from ..database import cache
from ..config import settings

logger = logging.getLogger(__name__)


INTENT_SYSTEM_PROMPT = """
Você é um especialista em classificação de intenção para um Bot de Agendamento.

Classifique a intenção do usuário em UMA destas categorias:

- SCHEDULING: Usuário quer marcar um horário, pergunta disponibilidade, aceita uma sugestão de horário.
- RESCHEDULE: Usuário quer trocar/alterar a data ou horário de um agendamento existente.
- CANCELLATION: Usuário quer cancelar um agendamento ou desistir do serviço.
- INFO: Usuário pede informações (preço, endereço, como funciona) ou tira dúvidas gerais.
- HUMAN_HANDOFF: Usuário pede para falar com atendente, pessoa real, humano ou está muito frustrado.

Retorne JSON:
{
  "intent": "SCHEDULING" | "RESCHEDULE" | "CANCELLATION" | "INFO" | "HUMAN_HANDOFF",
  "reason": "Breve explicação (max 100 chars)"
}
"""


class IntentTool:

    def __init__(self):
        self.cache_ttl = 1800  # 30 minutos
        self._load_patterns()

    def _load_patterns(self):
        """Carrega padrões Regex para classificação rápida"""

        self.scheduling_patterns = [
            r"\b(marcar|agendar|reservar)\b",
            r"\b(tem|têm)\s+(horário|vaga|disponibilidade)\b",
            r"\b(quero|gostaria de)\s+(ir|passar|fazer)\b",
            r"\b(pode ser|topo|fechado|combinado)\b",  # Aceite de sugestão
            r"\b(segunda|terça|quarta|quinta|sexta|sábado|domingo|amanhã|hoje)\b",  # Menção de data
            r"\b(\d{1,2})[h:](\d{2})?\b",  # Menção de hora (ex: 14h, 14:30)
        ]

        self.reschedule_patterns = [
            r"\b(trocar|mudar|alterar|remarcar|reagendar)\b",
            r"\b(não posso|imprevisto|surgiu um problema)\b.*\b(ir|comparecer)\b",
            r"\b(outra data|outro dia|outro horário)\b",
            r"\b(adiar|postergar)\b",
        ]

        self.cancellation_patterns = [
            r"\b(cancelar|desmarcar|anular)\b",
            r"\b(não vou|não quero)\s+(mais|ir|comparecer)\b",
            r"\b(desisto|esquece)\b",
        ]

        self.info_patterns = [
            r"\b(quanto|qual|valor|preço|custo)\b",
            r"\b(onde|endereço|local|fica)\b",
            r"\b(como funciona|quais os procedimentos)\b",
            r"\b(aceita|convênio|plano)\b",
        ]

        self.handoff_patterns = [
            r"\b(falar|conversar)\s+com\s+(alguém|atendente|humano|pessoa)\b",
            r"\b(preciso de ajuda|não estou entendendo)\b",
            r"\b(falar|ligar)\s+na\s+clínica\b",
        ]

    async def analyze(
        self, message: str, recent_history: List[Dict[str, str]]
    ) -> IntentAnalysisResult:
        try:
            cache_key = self._get_cache_key(message, recent_history)
            cached = cache.get(cache_key)
            if cached:
                logger.debug("Intent cache hit")
                return IntentAnalysisResult(**cached)

            # 1. Tenta Regex (Rápido e Barato)
            pattern_result = self._pattern_match(message)
            if pattern_result:
                cache.set(cache_key, pattern_result.model_dump(), self.cache_ttl)
                return pattern_result

            # 2. Fallback para LLM (Inteligente)
            result = await self._call_llm(message, recent_history)

            cache.set(cache_key, result.model_dump(), self.cache_ttl)
            return result

        except Exception as e:
            logger.error(f"Erro na análise de intenção: {e}")
            # Fallback seguro: Assume INFO para não travar fluxo
            return IntentAnalysisResult(
                intent=Intent.INFO,
                reason="Erro na análise, classificado como INFO por segurança",
            )

    def _pattern_match(self, message: str) -> Optional[IntentAnalysisResult]:
        message_lower = message.lower()

        # Ordem de prioridade importa
        for pattern in self.handoff_patterns:
            if re.search(pattern, message_lower):
                return IntentAnalysisResult(
                    intent=Intent.HUMAN_HANDOFF, reason="Regex: Handoff"
                )

        for pattern in self.cancellation_patterns:
            if re.search(pattern, message_lower):
                return IntentAnalysisResult(
                    intent=Intent.CANCELLATION, reason="Regex: Cancelamento"
                )

        for pattern in self.reschedule_patterns:
            if re.search(pattern, message_lower):
                return IntentAnalysisResult(
                    intent=Intent.RESCHEDULE, reason="Regex: Reagendamento"
                )

        for pattern in self.scheduling_patterns:
            if re.search(pattern, message_lower):
                return IntentAnalysisResult(
                    intent=Intent.SCHEDULING, reason="Regex: Agendamento"
                )

        for pattern in self.info_patterns:
            if re.search(pattern, message_lower):
                return IntentAnalysisResult(
                    intent=Intent.INFO, reason="Regex: Informação"
                )

        return None

    async def _call_llm(
        self, message: str, recent_history: List[Dict[str, str]]
    ) -> IntentAnalysisResult:

        history_text = self._format_history(recent_history)

        prompt = f"""Analise a intenção do cliente:
HISTÓRICO:
{history_text}
MENSAGEM: "{message}"
Retorne JSON."""

        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await openai_service.chat_completion(
            messages=messages,
            model=settings.TOOL_MODEL,  # gpt-4o-mini
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result_dict = json.loads(response["content"])
        return IntentAnalysisResult(**result_dict)

    def _format_history(self, recent_history: List[Dict[str, str]]) -> str:
        if not recent_history:
            return "(Sem histórico)"
        formatted = []
        for msg in recent_history[-4:]:
            role = "Cliente" if msg["role"] == "user" else "Agente"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _get_cache_key(self, message: str, recent_history: List[Dict[str, str]]) -> str:
        context = message
        if recent_history:
            context += "".join([m["content"] for m in recent_history[-2:]])
        hash_obj = hashlib.md5(context.encode())
        return f"intent_v2:{hash_obj.hexdigest()}"


intent_tool = IntentTool()
