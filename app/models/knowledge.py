from pydantic import BaseModel, Field
from typing import Optional, List


class KnowledgeEntryCreate(BaseModel):
    """Modelo para criar nova entrada no knowledge base"""

    question: str = Field(min_length=5, description="Pergunta da FAQ")
    answer: str = Field(min_length=10, description="Resposta da FAQ")
    category: str = Field(description="Categoria (pagamento, boleto, pix, etc)")
    priority: int = Field(
        ge=1, le=5, default=3, description="Prioridade 1-5 (1=mais importante)"
    )


class KnowledgeEntryUpdate(BaseModel):
    """Modelo para atualizar entrada existente"""

    question: Optional[str] = Field(None, min_length=5)
    answer: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class KnowledgeEntry(BaseModel):
    """Modelo de resposta de uma entrada do knowledge base"""

    id: str = Field(description="ID da entrada")
    question: str
    answer: str
    category: str
    priority: int
    created_at: str
    updated_at: str


class FAQResponse(BaseModel):
    """Resposta de uma FAQ com score de relevância"""

    question: str
    answer: str
    category: str
    relevance_score: float = Field(ge=0, le=1, description="Score de relevância 0-1")


class KnowledgeListResponse(BaseModel):
    """Lista de entradas do knowledge base"""

    total: int
    entries: List[KnowledgeEntry]


class KnowledgeBulkCreate(BaseModel):
    """Modelo para criação em massa"""

    company_id: str
    entries: List[KnowledgeEntryCreate] = Field(min_length=1)


class KnowledgeBulkResponse(BaseModel):
    """Resposta da criação em massa"""

    status: str
    count: int
    ids: List[str]
