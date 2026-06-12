from core.exceptions.base import AppException


class BadRequestError(AppException):
    def __init__(
        self,
        message: str = "Bad request",
        *,
        code: str = "BAD_REQUEST",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=400, details=details)


class UnauthorizedError(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        code: str = "UNAUTHORIZED",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, details=details)


class ForbiddenError(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        code: str = "FORBIDDEN",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403, details=details)


class NotFoundError(AppException):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        code: str = "NOT_FOUND",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, details=details)


class ConflictError(AppException):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        code: str = "CONFLICT",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=409, details=details)


class ValidationError(AppException):
    def __init__(
        self,
        message: str = "Validation error",
        *,
        code: str = "VALIDATION_ERROR",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=422, details=details)


class InvalidTokenError(UnauthorizedError):
    def __init__(
        self,
        message: str = "Invalid or expired token",
        *,
        code: str = "INVALID_TOKEN",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)
