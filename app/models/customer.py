from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CustomerProfile(BaseModel):

    telefone: str = Field(description="Chave primária (WhatsApp ID)")
    nome: Optional[str] = Field(None, description="Nome do cliente")
    email: Optional[str] = Field(None, description="E-mail para confirmação (opcional)")
    is_data_complete: bool = Field(
        default=False, description="Se True, pode prosseguir para agendamento"
    )
    last_interaction: datetime = Field(default_factory=datetime.now)

    def check_completion(self) -> bool:
        has_name = bool(self.nome and len(self.nome.strip()) > 1)
        self.is_data_complete = has_name
        return self.is_data_complete

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data["is_data_complete"] = self.check_completion()
        return data
