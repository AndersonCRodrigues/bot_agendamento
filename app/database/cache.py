from typing import Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    """Cache simples em memória com TTL"""

    def __init__(self):
        self._cache: dict = {}
        self._ttls: dict = {}

    def get(self, key: str) -> Optional[Any]:
        """Recupera valor do cache"""
        # Verifica se expirou
        if key in self._ttls:
            if datetime.now() > self._ttls[key]:
                # Expirou, remove
                self._cache.pop(key, None)
                self._ttls.pop(key, None)
                return None

        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Armazena valor no cache com TTL"""
        self._cache[key] = value
        self._ttls[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key: str):
        """Remove valor do cache"""
        self._cache.pop(key, None)
        self._ttls.pop(key, None)

    def clear(self):
        """Limpa todo o cache"""
        self._cache.clear()
        self._ttls.clear()

    def cleanup_expired(self):
        """Remove entradas expiradas (chamada periódica opcional)"""
        now = datetime.now()
        expired_keys = [key for key, expiry in self._ttls.items() if now > expiry]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._ttls.pop(key, None)

        if expired_keys:
            logger.debug(f"Cache cleanup: {len(expired_keys)} entradas removidas")


# Instância global
cache = MemoryCache()
