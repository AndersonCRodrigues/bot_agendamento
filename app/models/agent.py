from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    PROCESSING = "PROCESSING"
    WAITING_USER = "WAITING_USER"
    HANDOFF = "HANDOFF"
    FINISHED = "FINISHED"


class Sentiment(str, Enum):
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"
    RAIVA = "raiva"
    ANSIOSO = "ansioso"
    CONFUSO = "confuso"
    ENVERGONHADO = "envergonhado"  # Mantido para compatibilidade, mas menos usado
    TRISTE = "triste"


class Intent(str, Enum):
    # Foco exclusivo em Agendamento conforme PDF
    SCHEDULING = "SCHEDULING"  # Quero marcar, tem horário?
    RESCHEDULE = "RESCHEDULE"  # Quero trocar data
    CANCELLATION = "CANCELLATION"  # Cancelar
    INFO = "INFO"  # Preço, endereço, como funciona
    HUMAN_HANDOFF = "HUMAN_HANDOFF"  # Falar com atendente


class KanbanStatus(str, Enum):
    # Status visuais para o CRM
    NOVO_LEAD = "Novo Lead"
    EM_ATENDIMENTO = "Em Atendimento"
    AGENDADO = "Agendado"
    REAGENDAMENTO = "Reagendamento"
    CANCELADO = "Cancelado"
    HANDOFF_HUMANO = "Handoff Humano"
    SEM_INTERESSE = "Sem Interesse"
    DUVIDA = "Dúvida/Info"


class SentimentAnalysisResult(BaseModel):
    sentiment: Sentiment
    score: int = Field(ge=0, le=100)
    confidence: str


class IntentAnalysisResult(BaseModel):
    intent: Intent
    reason: str
