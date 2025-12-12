from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class CompanyConfig(BaseModel):
    nicho_mercado: str = Field(description="Ex: Clínica Médica, Barbearia, Estética")
    tom_voz: Literal["Profissional", "Amigável", "Formal", "Entusiasta"] = (
        "Profissional"
    )
    idioma: Literal["pt-BR", "en-US", "es-LA"] = "pt-BR"
    uso_emojis: bool = True
    frequencia_cta: Literal["minima", "normal", "maxima"] = "normal"
    estilo_despedida: str = "padrão"

    class Config:
        extra = "ignore"


class CompanyConfigDB(BaseModel):
    company_id: str
    config: CompanyConfig
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
