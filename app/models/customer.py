from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CustomerProfile(BaseModel):
    """
    Perfil do cliente focado em cadastro e agendamento.
    """

    telefone: str = Field(description="Chave primária (WhatsApp ID)")
    nome: Optional[str] = Field(None, description="Nome do cliente")
    email: Optional[str] = Field(None, description="E-mail para confirmação")
    is_data_complete: bool = Field(
        default=False, description="Se True, pode prosseguir para agendamento"
    )
    last_interaction: datetime = Field(default_factory=datetime.utcnow)

    def check_completion(self) -> bool:
        """Verifica se os dados obrigatórios existem"""
        has_name = bool(self.nome and len(self.nome.strip()) > 1)
        has_email = bool(self.email and "@" in self.email)
        self.is_data_complete = has_name and has_email
        return self.is_data_complete

    def model_dump(self, **kwargs):
        """Override para garantir compatibilidade"""
        data = super().model_dump(**kwargs)
        data["is_data_complete"] = self.check_completion()
        return data
