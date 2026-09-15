"""
Shared plumbing for agent tools: DB session handling, serialization, and a
consistent error shape. Every tool function should go through
`run_with_session` and `tool_error` so a domain exception becomes readable
JSON for Claude instead of an unhandled traceback that kills the graph run.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from app.core.database import SessionLocal
from app.core.exceptions import AppException
from app.models import ApprovalRequest, Mandate, Transaction

T = TypeVar("T")


def run_with_session(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T | dict:
    """Opens a session, runs fn(db, *args, **kwargs), closes the session.
    Converts AppException into the tool-error dict shape; lets anything
    else propagate (a truly unexpected bug should be loud, not swallowed)."""
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    except AppException as exc:
        return tool_error(exc)
    finally:
        db.close()


def tool_error(exc: AppException) -> dict:
    return {"error": exc.error_code, "message": exc.message, "detail": exc.detail}


def serialize_mandate(m: Mandate) -> dict:
    return {
        "mandate_id": str(m.id),
        "merchant_id": m.merchant_id,
        "merchant_name": m.merchant_name,
        "category": m.category,
        "amount_limit": float(m.amount_limit),
        "frequency": m.frequency,
        "next_payment_date": m.next_payment_date.isoformat(),
        "status": m.status,
        "paused_until": m.paused_until.isoformat() if m.paused_until else None,
        "pause_reason": m.pause_reason,
    }


def serialize_transaction(t: Transaction) -> dict:
    return {
        "transaction_id": str(t.id),
        "mandate_id": str(t.mandate_id) if t.mandate_id else None,
        "merchant_id": t.merchant_id,
        "merchant_name": t.merchant_name,
        "category": t.category,
        "amount": float(t.amount),
        "currency": t.currency,
        "payment_type": t.payment_type,
        "status": t.status,
        "provider_transaction_id": t.provider_transaction_id,
        "failure_reason": t.failure_reason,
        "created_at": t.created_at.isoformat(),
    }


def serialize_approval(a: ApprovalRequest) -> dict:
    return {
        "approval_id": str(a.id),
        "transaction_id": str(a.transaction_id),
        "reason": a.reason,
        "status": a.status,
        "expires_at": a.expires_at.isoformat(),
    }