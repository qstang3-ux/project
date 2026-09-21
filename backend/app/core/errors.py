from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__("RESOURCE_NOT_FOUND", message, 404)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "VERSION_CONFLICT") -> None:
        super().__init__(code, message, 409)


class SqlValidationError(AppError):
    def __init__(self, message: str = "生成的查询未通过安全校验") -> None:
        super().__init__("SQL_VALIDATION_FAILED", message, 422)
