"""
Custom exceptions for the whole app.

Why a custom hierarchy instead of raising HTTPException everywhere:
services and the agent's tools (Phase 6/7) need to raise domain errors
*without* importing FastAPI (they're not web-layer code). AppException is
plain Python; app.main registers one handler that turns any AppException
into the same JSON error shape everywhere in the API, and that handler is
the ONLY place that knows about HTTP status codes.

Error response shape (stable — the frontend can rely on this):
    {"error_code": "MANDATE_NOT_FOUND", "message": "...", "detail": {...}}
"""

from typing import Any


class AppException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"


class MandateNotFoundError(NotFoundError):
    error_code = "MANDATE_NOT_FOUND"


class TransactionNotFoundError(NotFoundError):
    error_code = "TRANSACTION_NOT_FOUND"


class ApprovalNotFoundError(NotFoundError):
    error_code = "APPROVAL_NOT_FOUND"


class UserNotFoundError(NotFoundError):
    error_code = "USER_NOT_FOUND"


class ValidationAppError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"


class DuplicatePaymentError(ConflictError):
    error_code = "DUPLICATE_PAYMENT"


class MandateStateError(AppException):
    """Mandate is CANCELLED/EXPIRED/PAUSED in a way that blocks the requested action."""

    status_code = 409
    error_code = "MANDATE_STATE_ERROR"


class PolicyViolationError(AppException):
    """Amount/category outside policy AND the caller tried to force execution anyway."""

    status_code = 403
    error_code = "POLICY_VIOLATION"


class ApprovalExpiredError(AppException):
    status_code = 409
    error_code = "APPROVAL_EXPIRED"


class PaymentProviderError(AppException):
    status_code = 502
    error_code = "PAYMENT_PROVIDER_ERROR"
