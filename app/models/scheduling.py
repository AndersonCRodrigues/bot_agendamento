from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ServiceInfo(BaseModel):
    """Informação compacta de serviço"""

    name: str
    duration: int
    price: float


class ProfessionalInfo(BaseModel):
    """Informação compacta de profissional"""

    name: str
    services: List[str]


class FullAgenda(BaseModel):

    professionals: Dict[str, ProfessionalInfo]
    services: Dict[str, ServiceInfo]
    availability: Dict[str, Dict[str, Dict[str, List[str]]]]

    class Config:
        json_schema_extra = {
            "example": {
                "professionals": {
                    "A1": {"name": "Ana Ribeiro", "services": ["S1", "S2"]},
                    "A2": {"name": "Maria Santos", "services": ["S1", "S3"]},
                },
                "services": {
                    "S1": {"name": "Limpeza de Pele", "duration": 60, "price": 180},
                    "S2": {"name": "Peeling Facial", "duration": 60, "price": 220},
                },
                "availability": {
                    "A1": {"S1": {"2025-12-10": ["08:00", "09:00", "10:00"]}}
                },
            }
        }


class FilteredAgenda(BaseModel):

    service_id: Optional[str] = None
    service_name: Optional[str] = None
    price: Optional[float] = None
    duration: Optional[int] = None
    options: List[Dict[str, any]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "S1",
                "service_name": "Limpeza de Pele",
                "price": 180,
                "duration": 60,
                "options": [
                    {
                        "professional": "Ana Ribeiro",
                        "professional_id": "A1",
                        "date": "2025-12-10",
                        "slots": ["08:00", "09:00", "10:00"],
                    },
                    {
                        "professional": "João Lima",
                        "professional_id": "A3",
                        "date": "2025-12-10",
                        "slots": ["08:00", "09:00"],
                    },
                ],
            }
        }


class AvailabilitySearchParams(BaseModel):
    """Parâmetros para busca de disponibilidade"""

    service_id: Optional[str] = None
    service_name: Optional[str] = None
    professional_id: Optional[str] = None
    professional_name: Optional[str] = None
    date: Optional[str] = None
    time_preference: Optional[str] = Field(
        None, description="morning, afternoon, evening"
    )
    max_results: int = Field(default=3, ge=1, le=10)


class AppointmentConfirmation(BaseModel):
    """Confirmação de agendamento - formato compacto"""

    professional_id: str
    service_id: str
    date: str
    time: str

    def to_human_readable(self, agenda: FullAgenda) -> str:
        """Converte para formato legível"""
        prof = agenda.professionals[self.professional_id]
        service = agenda.services[self.service_id]

        return (
            f"Profissional: {prof.name}\n"
            f"Serviço: {service.name}\n"
            f"Data: {self.date}\n"
            f"Horário: {self.time}\n"
            f"Duração: {service.duration}min\n"
            f"Valor: R$ {service.price:.2f}"
        )
