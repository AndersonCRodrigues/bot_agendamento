from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from .company import CompanyConfig


class GenericResponse(BaseModel):
    status: str
    detail: Optional[str] = None
    company_id: Optional[str] = None
    session_id: Optional[str] = None
    entry_id: Optional[str] = None


class OwnerInteractionResponse(BaseModel):
    status: str
    paused_until: str
    detail: str


class ConfigUpdateResponse(BaseModel):
    status: str
    company_id: str
    updated_at: str


class ConfigResponse(BaseModel):
    company_id: str
    config: CompanyConfig


class CompanyListItem(BaseModel):
    company_id: str
    nome_bot: str
    nicho_mercado: str
    created_at: str
    updated_at: str


class CompanyListResponse(BaseModel):
    total: int
    companies: List[CompanyListItem]


class KnowledgeOpResponse(BaseModel):
    status: str
    entry_id: str
    embedding_generated: Optional[bool] = None
    embedding_regenerated: Optional[bool] = None


class MetricsData(BaseModel):
    period: str
    interactions: int
    unique_sessions: int
    tokens: Dict[str, int]
    unique_companies: Optional[int] = None


class UsageMetricsResponse(BaseModel):
    company_id: str
    period: str
    filters: Dict[str, Optional[str]]
    data: List[MetricsData]
    optimization_note: str


class RankingItem(BaseModel):
    company_id: str
    total_tokens: int
    total_interactions: int
    unique_sessions: int


class RankingResponse(BaseModel):
    period: str
    ranking: List[RankingItem]


class HealthResponse(BaseModel):
    status: str
    service: Optional[str] = None
    version: Optional[str] = None
    checks: Optional[Dict[str, bool]] = None


class MessageSchema(BaseModel):
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class RagUsageSchema(BaseModel):
    question: str
    relevance_score: float
    used_at: datetime


class SessionSummarySchema(BaseModel):
    total_interactions: int
    sentiment_history: List[str] = []
    intent_history: List[str] = []
    last_kanban_status: Optional[str] = None
    rag_hits: int = 0


class SessionResponse(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    session_id: str
    company_id: str
    messages: List[MessageSchema]
    rag_context_used: List[RagUsageSchema]
    summary: SessionSummarySchema
    customer_context: Dict[str, Any]
    paused_until: Optional[datetime] = None
    last_sender_type: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    class Config:
        populate_by_name = True
