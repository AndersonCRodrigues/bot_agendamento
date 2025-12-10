from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "scheduling_bot"

    OPENAI_API_KEY: str

    REDIS_URL: Optional[str] = None
    USE_REDIS: bool = False

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.2
    EMBEDDING_DIMENSIONS: int = 512
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.3

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o"
    TOOL_MODEL: str = "gpt-4o-mini"

    SESSION_TTL_DAYS: int = 30

    OPENAI_TIMEOUT: float = 30.0

    MAX_REQUESTS_PER_MINUTE: int = 100
    MAX_REQUESTS_PER_SECOND: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
