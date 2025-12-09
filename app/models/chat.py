from pydantic import BaseModel, Field
from typing import List, Optional
from .agent import KanbanStatus
from .company import CompanyConfig
from .customer import CustomerProfile

# --- INPUT (REQUEST) ---


class Availability(BaseModel):
    """Um slot de horário disponível"""

    hora: str  # "14:00"
    disponivel: bool


class DaySchedule(BaseModel):
    """Agenda de um dia específico"""

    data: str  # "2023-10-27"
    slots: List[Availability]


class Service(BaseModel):
    id: str
    nome: str
    duracao_min: int
    preco: float


class Professional(BaseModel):
    id: str
    nome: str
    servicos: List[Service]
    # A agenda vem aqui (slots livres futuros)
    agenda_disponivel: List[DaySchedule] = Field(default_factory=list)


class CompanyPayload(BaseModel):
    id: str
    nome: str
    # O backend pode mandar a config no payload OU o bot busca no banco.
    # Para simplificar, assumimos que se vier aqui, sobrescreve.
    config_override: Optional[CompanyConfig] = None
    # A agenda completa disponível
    equipe: List[Professional] = Field(default_factory=list)


class CustomerPayload(BaseModel):
    telefone: str
    nome: Optional[str] = None
    email: Optional[str] = None
    mensagem: str


class ChatRequest(BaseModel):
    session_id: str
    company: CompanyPayload
    cliente: CustomerPayload


# --- OUTPUT (RESPONSE) ---


class UpdateUserDirective(BaseModel):
    """Diretiva: Atualizar cadastro no Backend Principal"""

    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class AppointmentDirective(BaseModel):
    """Diretiva: Criar agendamento no Backend Principal"""

    profissional_id: Optional[str] = None
    servico_id: Optional[str] = None
    data: Optional[str] = None
    hora: Optional[str] = None


class Directives(BaseModel):
    """Conjunto de ordens para o Backend (Zero-Write)"""

    type: str = Field(
        ..., description="'normal', 'update_user', 'appointment_confirmation'"
    )
    payload_update: Optional[UpdateUserDirective] = None
    payload_appointment: Optional[AppointmentDirective] = None


class CostInfo(BaseModel):
    """Métricas de consumo técnico (apenas tokens)"""

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ChatResponse(BaseModel):
    """Resposta final da API"""

    cliente_id: str
    company_id: str
    response_text: str

    # Kanban Status (Solicitado)
    kanban_status: KanbanStatus

    directives: Directives

    cost_info: Optional[CostInfo] = None

    metadata: dict = Field(default_factory=dict, description="Latência, debug, etc")
