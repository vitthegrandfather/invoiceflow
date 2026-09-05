"""Application errors with the public { error: { code, message, request_id } } shape."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        field_errors: list[dict[str, str]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.field_errors = field_errors
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class InvalidTransitionError(ConflictError):
    code = "INVALID_TRANSITION"


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ProviderMisconfiguredError(AppError):
    status_code = 503
    code = "PROVIDER_MISCONFIGURED"


class IdempotencyConflictError(ConflictError):
    code = "IDEMPOTENCY_CONFLICT"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


def error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    field_errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if field_errors:
        payload["error"]["field_errors"] = field_errors
    return payload
