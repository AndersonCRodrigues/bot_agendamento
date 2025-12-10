from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TokenUsageRecord(BaseModel):
    """
    Registro de consumo de tokens.
    Collection: 'token_usage'
    """

    company_id: str = Field(description="ID da empresa (Tenant)")
    session_id: str = Field(description="ID da sessão/cliente")
    timestamp: datetime = Field(default_factory=datetime.now)
    model: str = Field(default="gpt-4o")
    input_tokens: int
    output_tokens: int
    total_tokens: int
    node_name: Optional[str] = Field(None, description="Nó do grafo que gerou uso")
    date_str: str = Field(description="YYYY-MM-DD")
    month_str: str = Field(description="YYYY-MM")
    year_str: str = Field(description="YYYY")
    week_str: str = Field(description="YYYY-WW")


class TokenUsageAggregation(BaseModel):
    """Agregação de uso de tokens"""

    period: str
    interactions: int
    tokens: dict
    cost_estimate: Optional[float] = None


class UsageMetricsRequest(BaseModel):
    """Request para métricas de uso"""

    company_id: Optional[str] = None
    period: str = Field(
        default="daily", description="daily, weekly, monthly, yearly, total"
    )
    start_date: Optional[str] = None
    end_date: Optional[str] = None
