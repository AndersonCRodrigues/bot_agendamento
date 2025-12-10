from openai import AsyncOpenAI, OpenAIError, APITimeoutError, APIConnectionError
from typing import List, Dict, Any, Optional
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT
        )

    async def get_embedding(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding
        except APITimeoutError as e:
            logger.error(f"Timeout ao gerar embedding: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Erro de conexao ao gerar embedding: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"Erro OpenAI ao gerar embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao gerar embedding: {e}")
            raise

    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            if len(texts) > 2048:
                raise ValueError("Maximo de 2048 textos por batch")

            response = await self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
            return [item.embedding for item in response.data]
        except APITimeoutError as e:
            logger.error(f"Timeout ao gerar embeddings em lote: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Erro de conexao ao gerar embeddings em lote: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"Erro OpenAI ao gerar embeddings em lote: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao gerar embeddings em lote: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            params = {
                "model": model or settings.LLM_MODEL,
                "messages": messages,
                "temperature": (
                    temperature if temperature is not None else settings.TEMPERATURE
                ),
                "max_tokens": max_tokens or settings.MAX_TOKENS,
            }

            if response_format:
                params["response_format"] = response_format

            response = await self.client.chat.completions.create(**params)

            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
            }
        except APITimeoutError as e:
            logger.error(f"Timeout na chamada do chat: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Erro de conexao na chamada do chat: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"Erro OpenAI na chamada do chat: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado na chamada do chat: {e}")
            raise


openai_service = OpenAIService()
