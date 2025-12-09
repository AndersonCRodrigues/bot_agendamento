from pydantic import BaseModel, Field
from datetime import datetime


class TokenUsageRecord(BaseModel):
    """
    Registro técnico de consumo de tokens.
    Collection: 'token_usage'
    """

    company_id: str = Field(description="ID da empresa (Tenant)")
    session_id: str = Field(description="ID da sessão/cliente")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Métricas (Apenas Tokens)
    model: str = Field(default="gpt-4o")
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Metadados de Data (para agregação)
    date_str: str = Field(description="YYYY-MM-DD")
    month_str: str = Field(description="YYYY-MM")
    year_str: str = Field(description="YYYY")
