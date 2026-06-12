import logging
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from core.config import Settings
from core.schemas.responses import ErrorResponse

logger = logging.getLogger(__name__)
http_logger = logging.getLogger("http.request")

REQUEST_ID_HEADER = "X-Request-ID"
AUTH_RATE_LIMIT_PATHS = {"/auth/login", "/auth/register"}


class _InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


_rate_limiter = _InMemoryRateLimiter()


def register_middleware(app: FastAPI, settings: Settings) -> None:
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def auth_rate_limit_middleware(request: Request, call_next) -> Response:
        if settings.app_env == "production" and request.url.path in AUTH_RATE_LIMIT_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            allowed = _rate_limiter.is_allowed(
                f"{client_ip}:{request.url.path}",
                limit=settings.auth_rate_limit_per_minute,
                window_seconds=60,
            )
            if not allowed:
                request_id = getattr(request.state, "request_id", None)
                logger.warning(
                    "Auth rate limit exceeded for %s on %s",
                    client_ip,
                    request.url.path,
                    extra={"request_id": request_id, "path": request.url.path},
                )
                response = ErrorResponse(
                    message="Too many requests. Please try again later.",
                    code="RATE_LIMIT_EXCEEDED",
                    request_id=request_id,
                )
                return JSONResponse(
                    status_code=429,
                    content=response.model_dump(exclude_none=True),
                )
        return await call_next(request)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", None)
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        http_logger.info(
            "%s %s %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
