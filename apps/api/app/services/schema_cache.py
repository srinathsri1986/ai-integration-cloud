"""Connector schema cache — TTL-based in-process cache with optional Redis backend.

Architecture notes (SaaS):
- Mock connectors: schemas never change; cached indefinitely (TTL = 0 → no expiry).
- Live connectors: schemas can change when fields are added/removed; TTL = 5 minutes.
- Cache key: (connector_id, tenant_id or None) — each tenant's live schema is isolated.
- In-process dict works for single-process deployments (dev, single Uvicorn worker).
- Redis backend is used automatically when REDIS_URL is set in the environment, giving
  a shared cache across multiple Gunicorn/Uvicorn worker processes and Celery workers.
- Thread-safe: uses a threading.Lock for the in-process dict backend.
"""
from __future__ import annotations

import json
import logging
import os
import time
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Seconds before a live-connector schema is considered stale.
# Mock schemas are cached indefinitely (MOCK_TTL = None / unlimited).
LIVE_SCHEMA_TTL: int = int(os.environ.get("SCHEMA_CACHE_TTL_SECONDS", "300"))
MOCK_SCHEMA_TTL: int | None = None  # never expires

_CacheKey = tuple[str, int | None]  # (connector_id, tenant_id)


class _InProcessBackend:
    """Simple dict-based TTL cache — works for single-process deployments."""

    def __init__(self) -> None:
        self._store: dict[_CacheKey, tuple[Any, float | None]] = {}
        self._lock = Lock()

    def get(self, key: _CacheKey) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            with self._lock:
                self._store.pop(key, None)
            return None
        return value

    def set(self, key: _CacheKey, value: Any, ttl_seconds: int | None) -> None:
        expires_at = (time.monotonic() + ttl_seconds) if ttl_seconds is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def delete(self, key: _CacheKey) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear_connector(self, connector_id: str) -> None:
        with self._lock:
            keys = [k for k in self._store if k[0] == connector_id]
            for k in keys:
                del self._store[k]


class _RedisBackend:
    """Redis-backed cache — shared across all worker processes."""

    _PREFIX = "connector_schema:"

    def __init__(self, redis_url: str) -> None:
        import redis  # type: ignore[import]
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, key: _CacheKey) -> str:
        connector_id, tenant_id = key
        tenant_part = str(tenant_id) if tenant_id is not None else "global"
        return f"{self._PREFIX}{connector_id}:{tenant_part}"

    def get(self, key: _CacheKey) -> Any | None:
        try:
            raw = self._client.get(self._key(key))
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Schema cache Redis get failed: %s", exc)
            return None

    def set(self, key: _CacheKey, value: Any, ttl_seconds: int | None) -> None:
        try:
            serialised = json.dumps(value)
            if ttl_seconds is not None:
                self._client.setex(self._key(key), ttl_seconds, serialised)
            else:
                self._client.set(self._key(key), serialised)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Schema cache Redis set failed: %s", exc)

    def delete(self, key: _CacheKey) -> None:
        try:
            self._client.delete(self._key(key))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Schema cache Redis delete failed: %s", exc)

    def clear_connector(self, connector_id: str) -> None:
        try:
            pattern = f"{self._PREFIX}{connector_id}:*"
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Schema cache Redis clear failed: %s", exc)


def _build_backend() -> _InProcessBackend | _RedisBackend:
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        try:
            backend = _RedisBackend(redis_url)
            # Smoke-test the connection
            backend._client.ping()  # type: ignore[attr-defined]  # noqa: SLF001
            logger.info("Schema cache using Redis backend at %s", redis_url.split("@")[-1])
            return backend
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis not available (%s) — schema cache falling back to in-process dict.", exc)
    return _InProcessBackend()


class ConnectorSchemaCache:
    """Public facade used by the connector API and tests.

    Usage::

        schema_cache.get("netsuite", tenant_id=42)
        schema_cache.set("netsuite", schema_objects, tenant_id=42, is_mock=True)
        schema_cache.invalidate("netsuite", tenant_id=42)
        schema_cache.invalidate_connector("netsuite")  # all tenants
    """

    def __init__(self) -> None:
        self._backend = _build_backend()

    def _key(self, connector_id: str, tenant_id: int | None) -> _CacheKey:
        return (connector_id, tenant_id)

    def get(self, connector_id: str, tenant_id: int | None = None) -> list | None:
        return self._backend.get(self._key(connector_id, tenant_id))

    def set(
        self,
        connector_id: str,
        schema_objects: list,
        *,
        tenant_id: int | None = None,
        is_mock: bool = True,
    ) -> None:
        ttl = MOCK_SCHEMA_TTL if is_mock else LIVE_SCHEMA_TTL
        self._backend.set(self._key(connector_id, tenant_id), schema_objects, ttl)

    def invalidate(self, connector_id: str, tenant_id: int | None = None) -> None:
        """Invalidate schema cache for a specific (connector, tenant) pair."""
        self._backend.delete(self._key(connector_id, tenant_id))

    def invalidate_connector(self, connector_id: str) -> None:
        """Invalidate all cached schemas for a connector (all tenants)."""
        self._backend.clear_connector(connector_id)


# Module-level singleton
schema_cache = ConnectorSchemaCache()
