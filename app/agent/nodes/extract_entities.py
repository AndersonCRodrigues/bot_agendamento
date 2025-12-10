import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from ..state import GraphState

logger = logging.getLogger(__name__)


async def extract_entities_node(state: GraphState) -> GraphState:
    """
    Extrai entidades da mensagem do usuário SEM usar LLM.

    Entidades extraídas:
    - service_name: "limpeza de pele", "corte", etc
    - professional_name: "Ana", "Dr. João", etc
    - date_intent: "amanhã", "segunda", "dia 15"
    - time_intent: "manhã", "tarde", "14h"

    Economia: ~500 tokens por extração vs usar LLM
    """
    try:
        logger.info("[EXTRACT] Extraindo entidades da mensagem")

        message = state["user_message"].lower()
        entities: Dict[str, Any] = {}

        entities["service_name"] = _extract_service_name(message, state["full_agenda"])
        entities["professional_name"] = _extract_professional_name(
            message, state["full_agenda"]
        )
        entities["date_intent"] = _extract_date_intent(message)
        entities["time_preference"] = _extract_time_preference(message)
        entities["date_specific"] = _extract_specific_date(message)

        logger.info(f"[EXTRACT] Entidades: {entities}")

        return {**state, "extracted_entities": entities}

    except Exception as e:
        logger.error(f"[EXTRACT] Erro: {e}", exc_info=True)
        return {**state, "extracted_entities": {}, "error": str(e)}


def _extract_service_name(message: str, agenda) -> Optional[str]:
    """Extrai nome do serviço por matching de palavras-chave"""
    for service_id, service_info in agenda.services.items():
        service_name = service_info.name.lower()
        service_words = service_name.split()

        for word in service_words:
            if len(word) > 3 and word in message:
                return service_name

        if service_name in message:
            return service_name

    return None


def _extract_professional_name(message: str, agenda) -> Optional[str]:
    """Extrai nome do profissional"""
    for prof_id, prof_info in agenda.professionals.items():
        prof_name = prof_info.name.lower()
        first_name = prof_name.split()[0]

        if first_name in message or prof_name in message:
            return prof_name

        patterns = [
            rf"\b(dr|dra|doutor|doutora)\s+{first_name}\b",
            rf"\bcom\s+(o|a)?\s*{first_name}\b",
        ]

        for pattern in patterns:
            if re.search(pattern, message):
                return prof_name

    return None


def _extract_date_intent(message: str) -> Optional[str]:
    """Extrai intenção de data relativa"""
    date_patterns = {
        "hoje": "today",
        "amanhã": "tomorrow",
        "depois de amanhã": "day_after_tomorrow",
        "segunda": "monday",
        "terça": "tuesday",
        "quarta": "wednesday",
        "quinta": "thursday",
        "sexta": "friday",
        "sábado": "saturday",
        "domingo": "sunday",
        "próxima semana": "next_week",
        "semana que vem": "next_week",
        "mês que vem": "next_month",
    }

    for pattern, intent in date_patterns.items():
        if pattern in message:
            return intent

    return None


def _extract_specific_date(message: str) -> Optional[str]:
    """Extrai data específica em formato DD/MM ou DD-MM ou YYYY-MM-DD"""
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{2})[/-](\d{2})[/-](\d{4})",
        r"(\d{2})[/-](\d{2})",
        r"dia\s+(\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            groups = match.groups()

            if len(groups) == 3:
                if len(groups[0]) == 4:
                    return f"{groups[0]}-{groups[1]}-{groups[2]}"
                else:
                    year = datetime.now().year
                    return f"{year}-{groups[1]}-{groups[0]}"

            elif len(groups) == 2:
                year = datetime.now().year
                month = groups[1]
                day = groups[0]
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            elif len(groups) == 1:
                year = datetime.now().year
                month = datetime.now().month
                day = groups[0]
                return f"{year}-{str(month).zfill(2)}-{day.zfill(2)}"

    return None


def _extract_time_preference(message: str) -> Optional[str]:
    """Extrai preferência de horário"""
    if any(word in message for word in ["manhã", "cedo", "matinal"]):
        return "morning"

    if any(word in message for word in ["tarde", "depois do almoço"]):
        return "afternoon"

    if any(word in message for word in ["noite", "fim do dia", "após às 18"]):
        return "evening"

    time_match = re.search(r"(\d{1,2})[h:]?(\d{2})?", message)
    if time_match:
        hour = int(time_match.group(1))
        if hour < 12:
            return "morning"
        elif hour < 18:
            return "afternoon"
        else:
            return "evening"

    return None
