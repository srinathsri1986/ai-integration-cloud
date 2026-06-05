"""Request correlation ID and structured access logging middleware.

Every request gets a unique `request_id` (UUID4). It is:
  - Set in `request.state.request_id` for use by service-layer log calls
  - Stored in `_request_id_var` ContextVar so any logger in the call chain
    can include it without thread/async safety issues
  - Returned in the `X-Request-ID` response header for client-side tracing

Structured log record format (JSON via python-json-logger):
  {
    "event": "request",
    "requestId": "...",
    "method": "GET",
    "path": "/api/v1/flows",
    "statusCode": 200,
    "durationMs": 12
  }
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# ContextVar so any code in the request chain can read the current request_id
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the request ID for the currently executing request (if any)."""
    return _request_id_var.get()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any):
        request_id = str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "request",
            extra={
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "statusCode": response.status_code,
                "durationMs": duration_ms,
            },
        )

        response.headers["X-Request-ID"] = request_id
        _request_id_var.reset(token)
        return response
