from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente"""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cobranca_bot"

    # OpenAI
    OPENAI_API_KEY: str

    # Redis
    REDIS_URL: Optional[str] = None
    USE_REDIS: bool = False

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Agent Config
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.2
    EMBEDDING_DIMENSIONS: int = 512
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.3

    # Models
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o"
    TOOL_MODEL: str = "gpt-4o-mini"

    # Session
    SESSION_TTL_DAYS: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global de settings
settings = Settings()
