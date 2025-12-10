from typing import Any, Optional
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self):
        self._cache: dict = {}
        self._ttls: dict = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._ttls:
                if datetime.now() > self._ttls[key]:
                    self._cache.pop(key, None)
                    self._ttls.pop(key, None)
                    return None
            return self._cache.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        with self._lock:
            self._cache[key] = value
            self._ttls[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)
            self._ttls.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._ttls.clear()

    def cleanup_expired(self):
        with self._lock:
            now = datetime.now()
            expired_keys = [key for key, expiry in self._ttls.items() if now > expiry]
            for key in expired_keys:
                self._cache.pop(key, None)
                self._ttls.pop(key, None)
            if expired_keys:
                logger.debug(f"Cache cleanup: {len(expired_keys)} entradas removidas")


cache = MemoryCache()
