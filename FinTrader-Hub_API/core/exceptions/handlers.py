import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions.base import AppException
from core.schemas.responses import ErrorResponse

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = _get_request_id(request)
        response = ErrorResponse(
            message=exc.message,
            code=exc.code,
            details=exc.details,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(exclude_none=True),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = _get_request_id(request)
        response = ErrorResponse(
            message=str(exc.detail),
            code="HTTP_ERROR",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        response = ErrorResponse(
            message="Request validation failed",
            code="VALIDATION_ERROR",
            details=exc.errors(),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response.model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id, "path": request.url.path},
            exc_info=exc,
        )
        response = ErrorResponse(
            message="Internal server error",
            code="INTERNAL_ERROR",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(exclude_none=True),
        )
