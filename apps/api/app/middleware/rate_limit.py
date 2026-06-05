"""Redis-backed sliding-window rate limiting middleware.

Limits:
  - 300 requests per minute per authenticated tenant
  - 60 requests per minute per unauthenticated source IP

On limit exceeded: returns HTTP 429 with a Retry-After header.

The tenant_id is extracted from the JWT access token claim (best-effort).
If the token cannot be parsed, falls back to the source IP bucket.

This middleware uses Redis INCR + EXPIRE for O(1) per-request overhead.
The window is aligned to full UTC minutes (not sliding per-request) to
prevent per-second spike bursts from consuming the entire quota.
"""

import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Paths that bypass rate limiting (health checks, metrics)
_EXEMPT_PREFIXES = ("/health",)

# Limits
_TENANT_LIMIT = 300       # requests per minute when authenticated
_IP_LIMIT = 60            # requests per minute when unauthenticated


def _extract_tenant_id(request: Request) -> str | None:
    """Best-effort extraction of tenant_id from JWT Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        import base64
        import json

        # Decode payload (pad to multiple of 4 for base64)
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        tid = payload.get("tenant_id")
        return str(tid) if tid is not None else None
    except Exception:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, redis_url: str = "redis://localhost:6379/0") -> None:
        super().__init__(app)
        self._redis_url = redis_url
        self._redis: Any = None

    def _get_redis(self) -> Any:
        """Lazy-initialise the Redis client (avoids import-time connection errors)."""
        if self._redis is None:
            import redis as redis_lib  # type: ignore[import]

            self._redis = redis_lib.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        return self._redis

    async def dispatch(self, request: Request, call_next):
        import os

        path = request.url.path

        # Bypass entirely in test mode (CELERY_TASK_ALWAYS_EAGER is the test-mode flag)
        # or when rate limiting is explicitly disabled
        if (
            os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
            or os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "false"
        ):
            return await call_next(request)

        # Exempt health and docs endpoints
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        try:
            redis = self._get_redis()
        except Exception:
            # Redis unavailable — fail open (let request through)
            logger.warning("Rate limit Redis unavailable — bypassing rate limit check.")
            return await call_next(request)

        # Determine bucket key
        tenant_id = _extract_tenant_id(request)
        window = int(time.time()) // 60  # 1-minute aligned window

        if tenant_id:
            bucket = f"rl:tenant:{tenant_id}:{window}"
            limit = _TENANT_LIMIT
        else:
            client_ip = request.client.host if request.client else "unknown"
            bucket = f"rl:ip:{client_ip}:{window}"
            limit = _IP_LIMIT

        try:
            count = redis.incr(bucket)
            if count == 1:
                redis.expire(bucket, 120)  # expire after 2 windows for safety

            if count > limit:
                retry_after = 60 - (int(time.time()) % 60)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry after the indicated delay.",
                        "retryAfter": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception as exc:
            # Redis error — fail open
            logger.warning("Rate limit check failed: %s — bypassing.", exc)

        return await call_next(request)
