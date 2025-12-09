from typing import TypedDict, List, Dict, Optional, Annotated, Any
from operator import add
from ..models import (
    SentimentAnalysisResult,
    IntentAnalysisResult,
    ChatResponse,
    FAQResponse,
)


class GraphState(TypedDict):
    # Inputs Iniciais
    company_id: str
    session_id: str
    user_message: str
    start_chat: Optional[str]

    # Objetos Ricos (Pydantic convertidos para dict ou objetos)
    company_config: Dict[str, Any]  # As 15 dimensões
    customer_profile: Dict[str, Any]  # O perfil (nome, email, status)
    company_agenda: List[Dict[str, Any]]  # A lista de profissionais/serviços

    # Histórico
    chat_history: List[Dict]
    recent_history: List[Dict]

    # RAG (FAQ)
    rag_knowledge: List[FAQResponse]
    rag_formatted: str

    # Análises (Tools)
    sentiment_result: Optional[SentimentAnalysisResult]
    intent_result: Optional[IntentAnalysisResult]

    # Flags de Controle
    sentiment_analyzed: bool
    intent_analyzed: bool
    tools_validated: bool

    # Resultado da "Barreira de Cadastro"
    is_data_complete: bool

    # Saída Final
    final_response: Optional[ChatResponse]

    # Metadados
    tools_called: Annotated[List[str], add]
    prompt_tokens: int
    completion_tokens: int
    error: Optional[str]
