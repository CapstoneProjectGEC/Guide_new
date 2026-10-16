"""Middleware components for request tracing and correlation IDs."""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from backend.src.core.logging import correlation_id_ctx, get_logger

logger = get_logger("core.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware extracting or generating X-Correlation-ID for each request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check for client-supplied correlation ID or generate fresh UUID
        cid = request.headers.get("X-Correlation-ID")
        if not cid or not cid.strip():
            cid = str(uuid.uuid4())

        token = correlation_id_ctx.set(cid)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Correlation-ID"] = cid
            response.headers["X-Process-Time-Ms"] = str(duration_ms)

            # Log request completion with duration and status code
            logger.info(
                "http_request_processed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        finally:
            correlation_id_ctx.reset(token)
