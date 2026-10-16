"""Typed domain errors and standardized exception handlers."""

from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.src.core.logging import correlation_id_ctx, get_logger

logger = get_logger("core.errors")


class ErrorDetail(BaseModel):
    """Standardized error contract."""

    code: str = Field(description="Machine-readable error identifier")
    message: str = Field(description="Human-readable explanation of error")
    details: dict[str, Any] = Field(default_factory=dict, description="Contextual error details")
    correlation_id: str = Field(description="Unique request tracing identifier")


class ErrorEnvelope(BaseModel):
    """Standard top-level error response envelope."""

    error: ErrorDetail


class AppException(Exception):
    """Base domain exception for application-level errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str = "Requested resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class ValidationError(AppException):
    """Business validation failure."""

    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422, details=details)


class AuthenticationError(AppException):
    """Authentication required or invalid."""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class PermissionDeniedError(AppException):
    """Insufficient privileges."""

    def __init__(self, message: str = "Permission denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictError(AppException):
    """Resource state conflict."""

    def __init__(self, message: str = "Resource conflict", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class ServiceUnavailableError(AppException):
    """External or internal dependency temporarily down."""

    def __init__(self, message: str = "Service temporarily unavailable", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="SERVICE_UNAVAILABLE", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


class AudioValidationError(AppException):
    """Audio payload or format validation failure."""

    def __init__(self, message: str = "Invalid audio input", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="AUDIO_VALIDATION_ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class AudioTooLargeError(AppException):
    """Audio payload exceeds allowed size limit."""

    def __init__(self, message: str = "Audio file exceeds maximum size limit", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="AUDIO_TOO_LARGE", status_code=status.HTTP_413_CONTENT_TOO_LARGE, details=details)


class AudioTimeoutError(AppException):
    """Audio transcription operation timed out."""

    def __init__(self, message: str = "Speech transcription timed out", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="AUDIO_TIMEOUT", status_code=status.HTTP_504_GATEWAY_TIMEOUT, details=details)


class TTSValidationError(AppException):
    """Text synthesis validation failure (e.g. empty or blank text, unsupported language)."""

    def __init__(self, message: str = "Invalid text input for speech synthesis", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="TTS_VALIDATION_ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class TTSTooLargeError(AppException):
    """Synthesis input text exceeds allowed character limit."""

    def __init__(self, message: str = "Text exceeds maximum synthesis length limit", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="TTS_TOO_LARGE", status_code=status.HTTP_413_CONTENT_TOO_LARGE, details=details)


class TTSUnavailableError(AppException):
    """TTS engine disabled or requested voice model is unavailable."""

    def __init__(self, message: str = "Speech synthesis service or model voice is unavailable", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="TTS_UNAVAILABLE", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


class TTSTimeoutError(AppException):
    """Speech synthesis operation timed out."""

    def __init__(self, message: str = "Speech synthesis timed out", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="TTS_TIMEOUT", status_code=status.HTTP_504_GATEWAY_TIMEOUT, details=details)


class RateLimitExceededError(AppException):
    """Client request frequency exceeds rate limit threshold."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please wait before retrying.",
        retry_after: int = 60,
        limit: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        det = details or {}
        det["retry_after_seconds"] = retry_after
        det["limit_requests_per_minute"] = limit
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=det,
        )
        self.retry_after = retry_after
        self.limit = limit


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform error handlers on FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        cid = correlation_id_ctx.get()
        logger.warning(
            "app_exception_occurred",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            path=request.url.path,
        )
        payload = ErrorEnvelope(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                correlation_id=cid,
            )
        )
        headers = {}
        if isinstance(exc, RateLimitExceededError):
            headers["Retry-After"] = str(exc.retry_after)
            headers["X-RateLimit-Limit"] = str(exc.limit)
            headers["X-RateLimit-Remaining"] = "0"
            headers["X-RateLimit-Reset"] = str(exc.retry_after)

        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(), headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        cid = correlation_id_ctx.get()
        logger.info("request_validation_failed", path=request.url.path, errors=exc.errors())
        payload = ErrorEnvelope(
            error=ErrorDetail(
                code="REQUEST_VALIDATION_ERROR",
                message="Incoming request failed schema validation.",
                details={"errors": exc.errors()},
                correlation_id=cid,
            )
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        cid = correlation_id_ctx.get()
        logger.error("unhandled_system_exception", path=request.url.path, error=str(exc), exc_info=True)
        payload = ErrorEnvelope(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
                details={},
                correlation_id=cid,
            )
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())
