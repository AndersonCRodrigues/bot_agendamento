from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from .agent import KanbanStatus
from .company import CompanyConfig


class CompanyPayload(BaseModel):
    """Payload da empresa com agenda otimizada"""

    id: str
    nome: str
    config_override: Optional[CompanyConfig] = None
    agenda: Dict[str, Any] = Field(
        description="Agenda no formato otimizado: {professionals, services, availability}"
    )


class CustomerPayload(BaseModel):
    """Dados do cliente"""

    telefone: str
    nome: Optional[str] = None
    email: Optional[str] = None
    mensagem: str


class ChatRequest(BaseModel):
    """Request otimizado - agenda compacta com IDs curtos"""

    session_id: str
    company: CompanyPayload
    cliente: CustomerPayload


class UpdateUserDirective(BaseModel):
    """Diretiva: Atualizar cadastro"""

    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class AppointmentDirective(BaseModel):
    """Diretiva: Criar agendamento com todos os IDs necessários"""

    profissional_id: str
    profissional_name: Optional[str] = None
    servico_id: str
    servico_name: Optional[str] = None
    data: str
    hora: str


class Directives(BaseModel):
    """Conjunto de ordens para o Backend"""

    type: str = Field(
        ..., description="'normal', 'update_user', 'appointment_confirmation'"
    )
    payload_update: Optional[UpdateUserDirective] = None
    payload_appointment: Optional[AppointmentDirective] = None


class CostInfo(BaseModel):
    """Métricas de consumo"""

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Optional[float] = None


class ChatResponse(BaseModel):
    """Resposta final da API"""

    cliente_id: str
    company_id: str
    response_text: str
    kanban_status: KanbanStatus
    directives: Directives
    cost_info: Optional[CostInfo] = None
    metadata: dict = Field(default_factory=dict)
