from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Serviço para interações com OpenAI API"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def get_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um texto

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding
        """
        try:
            response = await self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            raise

    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings em lote (até 2048 textos)

        Args:
            texts: Lista de textos

        Returns:
            Lista de embeddings
        """
        try:
            if len(texts) > 2048:
                raise ValueError("Máximo de 2048 textos por batch")

            response = await self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings em lote: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Gera resposta do chat

        Args:
            messages: Lista de mensagens no formato OpenAI
            model: Modelo a usar (default: settings.LLM_MODEL)
            temperature: Temperatura (default: settings.TEMPERATURE)
            max_tokens: Máximo de tokens (default: settings.MAX_TOKENS)
            response_format: Formato da resposta (ex: {"type": "json_object"})

        Returns:
            Resposta completa da API
        """
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
        except Exception as e:
            logger.error(f"Erro na chamada do chat: {e}")
            raise


# Instância global
openai_service = OpenAIService()
