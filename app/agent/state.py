from typing import TypedDict, List, Dict, Optional, Annotated, Any
from operator import add
from ..models.agent import SentimentAnalysisResult, IntentAnalysisResult
from ..models.chat import ChatResponse
from ..models.scheduling import FullAgenda, FilteredAgenda


class GraphState(TypedDict):
    """
    Estado otimizado do grafo.

    IMPORTANTE:
    - full_agenda NUNCA vai para o LLM (economiza ~8000 tokens)
    - filtered_agenda é o que o LLM vê (apenas 50-200 tokens)
    """

    company_id: str
    session_id: str
    user_message: str

    company_config: Dict[str, Any]
    customer_profile: Dict[str, Any]

    full_agenda: FullAgenda
    filtered_agenda: Optional[FilteredAgenda]

    chat_history: List[Dict]
    recent_history: List[Dict]

    sentiment_result: Optional[SentimentAnalysisResult]
    intent_result: Optional[IntentAnalysisResult]

    sentiment_analyzed: bool
    intent_analyzed: bool
    tools_validated: bool

    is_data_complete: bool

    extracted_entities: Dict[str, Any]

    final_response: Optional[ChatResponse]

    tools_called: Annotated[List[str], add]
    prompt_tokens: int
    completion_tokens: int
    error: Optional[str]

    llm_response_raw: Dict[str, Any]
