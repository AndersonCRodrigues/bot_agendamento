from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime


class CompanyConfig(BaseModel):
    """
    Configuração comportamental do Bot (As 15 Dimensões).
    Armazenado na collection 'companies'.
    """

    nicho_mercado: str = Field(
        default="Serviços Gerais", description="Ex: Clínica Médica, Barbearia"
    )
    nome_bot: str = Field(
        default="Assistente", description="Nome do assistente virtual"
    )
    enfase_confidencialidade: bool = Field(
        default=False,
        description="Se True, reforça avisos de privacidade (Saúde/Jurídico)",
    )
    vocabularios_especificos: Dict[str, str] = Field(
        default_factory=dict, description="Ex: {'cliente': 'paciente'}"
    )
    permitir_girias: bool = Field(default=False)
    tom_voz: str = Field(
        default="Profissional Neutro", description="Ex: Amigável, Formal, Entusiasta"
    )
    nivel_empatia: str = Field(default="Médio", description="Baixo, Médio, Alto")
    estilo_tratamento: str = Field(default="Você", description="Você, Sr(a), Tu")
    uso_emojis: str = Field(default="moderado", description="nenhum, moderado, intenso")
    foco_conversa: str = Field(
        default="Agendamento Direto", description="Prioridade máxima do bot"
    )
    extensao_respostas: str = Field(default="concisa", description="concisa, detalhada")
    estilo_persuasao: str = Field(
        default="suave", description="suave, urgente (escassez)"
    )
    reacao_erros: str = Field(
        default="educada", description="Como reagir a inputs inválidos"
    )
    frequencia_reforco_positivo: str = Field(
        default="baixa", description="Uso de 'Ótimo!', 'Perfeito!'"
    )
    frequencia_cta: str = Field(
        default="normal", description="Frequência de chamadas para ação"
    )
    estilo_despedida: str = Field(default="padrão", description="Ex: Cordial, Formal")

    class Config:
        extra = "ignore"


class CompanyConfigDB(BaseModel):
    """Modelo para persistência no MongoDB"""

    company_id: str
    config: CompanyConfig
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
