"""Sliding-window rate limiter and middleware protecting tourist and admin endpoints."""

import asyncio
from dataclasses import dataclass
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.src.core.config import get_settings
from backend.src.core.errors import ErrorDetail, ErrorEnvelope
from backend.src.core.logging import correlation_id_ctx, get_logger
from backend.src.core.security import decode_token

logger = get_logger("core.limiter")


@dataclass
class RateLimitResult:
    """Outcome of a rate limit evaluation."""

    is_allowed: bool
    limit: int | None
    remaining: int | None
    retry_after: int
    client_type: str
    client_key: str


class RateLimiter:
    """Thread-safe in-memory sliding-window rate limiter using monotonic clock.

    Note:
        Rate limit counters are tracked in-memory per server process and reset on
        application restart. Multi-worker deployments under a reverse proxy (e.g. Nginx)
        distribute traffic across workers. Bounded storage caps memory growth.
    """

    EXEMPT_PATHS: set[str] = {
        "/health",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.RATE_LIMIT_ENABLED
        self.tourist_rpm = self.settings.RATE_LIMIT_TOURIST_RPM
        self.admin_rpm = self.settings.RATE_LIMIT_ADMIN_RPM
        self.window_seconds = self.settings.RATE_LIMIT_WINDOW_SECONDS
        self.max_tracked_clients = self.settings.RATE_LIMIT_MAX_TRACKED_CLIENTS
        self.trusted_proxies = set(self.settings.TRUSTED_PROXIES)

        self._clients: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    def is_exempt(self, request: Request) -> bool:
        """Check whether request is exempt from rate limiting."""
        if request.method == "OPTIONS":
            return True

        path = request.url.path.rstrip("/")
        if not path:
            path = "/"
        return path in self.EXEMPT_PATHS or request.url.path in self.EXEMPT_PATHS

    def extract_client_identifier(self, request: Request) -> tuple[str, str, int]:
        """Classify client as authenticated admin or anonymous tourist and return limit.

        Security Note:
            Client-supplied role headers (e.g., X-Role, X-Admin) are strictly ignored.
            Admin status is granted ONLY if a valid, unexpired Bearer access token is verified.
            X-Forwarded-For is trusted ONLY when the direct peer socket is in TRUSTED_PROXIES.

        Returns:
            tuple[str, str, int]: (client_key, client_type, limit_rpm)
        """
        # 1. Attempt trusted Bearer token verification for Admin role
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_token(token)
                if payload.get("type") == "access" and payload.get("sub"):
                    admin_id = payload["sub"]
                    return f"admin:{admin_id}", "admin", self.admin_rpm
            except Exception:
                # Token invalid or expired -> falls back to tourist quota
                pass

        # 2. Anonymous tourist client: resolve IP taking proxy into account
        peer_host = request.client.host if request.client else "127.0.0.1"

        if peer_host in self.trusted_proxies:
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for and x_forwarded_for.strip():
                client_ip = x_forwarded_for.split(",")[0].strip()
            else:
                client_ip = peer_host
        else:
            # Direct untrusted client: ignore spoofed forwarding headers
            client_ip = peer_host

        return f"tourist:{client_ip}", "tourist", self.tourist_rpm

    def _cleanup_stale_records(self, now: float, window_start: float) -> None:
        """Purge expired timestamps and prune inactive keys."""
        to_delete = []
        for key, timestamps in self._clients.items():
            valid = [t for t in timestamps if t > window_start]
            if not valid:
                to_delete.append(key)
            else:
                self._clients[key] = valid

        for key in to_delete:
            self._clients.pop(key, None)

        # Enforce hard capacity ceiling if still too large
        if len(self._clients) > self.max_tracked_clients:
            excess = len(self._clients) - self.max_tracked_clients
            # Pop oldest keys
            for _ in range(excess):
                self._clients.pop(next(iter(self._clients)), None)

    async def check_rate_limit(self, request: Request) -> RateLimitResult:
        """Evaluate rate limit window for incoming request using monotonic clock."""
        if not self.enabled or self.is_exempt(request):
            return RateLimitResult(
                is_allowed=True,
                limit=None,
                remaining=None,
                retry_after=0,
                client_type="exempt",
                client_key="exempt",
            )

        client_key, client_type, limit = self.extract_client_identifier(request)
        now = time.monotonic()
        window_start = now - self.window_seconds

        async with self._lock:
            # Periodic cleanup every 30 seconds
            if now - self._last_cleanup > 30.0 or len(self._clients) > self.max_tracked_clients:
                self._cleanup_stale_records(now, window_start)
                self._last_cleanup = now

            timestamps = [t for t in self._clients.get(client_key, []) if t > window_start]

            if len(timestamps) >= limit:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + self.window_seconds - now))
                logger.warning(
                    "rate_limit_exceeded",
                    client_key=client_key,
                    client_type=client_type,
                    limit=limit,
                    retry_after=retry_after,
                    path=request.url.path,
                )
                return RateLimitResult(
                    is_allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after=retry_after,
                    client_type=client_type,
                    client_key=client_key,
                )

            timestamps.append(now)
            self._clients[client_key] = timestamps
            remaining = max(0, limit - len(timestamps))

            return RateLimitResult(
                is_allowed=True,
                limit=limit,
                remaining=remaining,
                retry_after=0,
                client_type=client_type,
                client_key=client_key,
            )

    def reset_sync(self) -> None:
        """Synchronously reset all tracked client counters (primarily for testing)."""
        self._clients.clear()
        self._last_cleanup = time.monotonic()

    async def reset(self) -> None:
        """Reset all tracked client counters (primarily for testing)."""
        async with self._lock:
            self.reset_sync()


_limiter_singleton: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Return cached singleton RateLimiter instance."""
    global _limiter_singleton
    if _limiter_singleton is None:
        _limiter_singleton = RateLimiter()
    return _limiter_singleton


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware evaluating request rate limits and appending quota headers."""

    def __init__(self, app: Any, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        res = await self.limiter.check_rate_limit(request)

        if not res.is_allowed:
            cid = correlation_id_ctx.get()
            payload = ErrorEnvelope(
                error=ErrorDetail(
                    code="RATE_LIMIT_EXCEEDED",
                    message=f"Rate limit of {res.limit} requests per minute exceeded. Please retry after {res.retry_after} seconds.",
                    details={
                        "retry_after_seconds": res.retry_after,
                        "limit_requests_per_minute": res.limit,
                        "client_type": res.client_type,
                    },
                    correlation_id=cid,
                )
            )
            headers = {
                "Retry-After": str(res.retry_after),
                "X-RateLimit-Limit": str(res.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(res.retry_after),
            }
            return JSONResponse(status_code=429, content=payload.model_dump(), headers=headers)

        response = await call_next(request)

        # Attach rate limit quota headers for non-exempt requests
        if res.limit is not None and res.remaining is not None:
            response.headers["X-RateLimit-Limit"] = str(res.limit)
            response.headers["X-RateLimit-Remaining"] = str(res.remaining)

        return response
