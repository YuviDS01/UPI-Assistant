"""
Agent tools for mandate lifecycle: create, cancel, pause, resume.

Every function here does exactly one thing: parse Claude's arguments and
call the matching MandateService method. No policy logic, no status
transitions decided here — that all lives in MandateService (Phase 6).
"""

import uuid
from datetime import date

from langchain_core.tools import tool

from app.agent.tools._common import run_with_session, serialize_mandate
from app.services.mandate_service import MandateService


@tool
def create_mandate(
    user_id: str,
    merchant_id: str,
    merchant_name: str,
    category: str,
    amount_limit: float,
    frequency: str,
    next_payment_date: str,
) -> dict:
    """
    Create a new recurring payment mandate. frequency is one of DAILY,
    WEEKLY, MONTHLY, YEARLY. next_payment_date is an ISO date (YYYY-MM-DD).
    Only call this after the user has explicitly confirmed the merchant,
    amount limit, and frequency.
    """

    def _run(db):
        mandate = MandateService.create_mandate(
            db,
            user_id=uuid.UUID(user_id),
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            amount_limit=amount_limit,
            frequency=frequency,
            next_payment_date=date.fromisoformat(next_payment_date),
        )
        return serialize_mandate(mandate)

    return run_with_session(_run)


@tool
def cancel_mandate(mandate_id: str) -> dict:
    """
    Permanently cancel a mandate. This is terminal — the mandate can never
    be resumed after this. Only call this after explicit user confirmation.
    If the user might want to stop payments temporarily, use pause_mandate
    instead — it does not require re-authorization to undo.
    """

    def _run(db):
        mandate = MandateService.cancel_mandate(db, uuid.UUID(mandate_id))
        return serialize_mandate(mandate)

    return run_with_session(_run)


@tool
def pause_mandate(mandate_id: str, paused_until: str | None = None, reason: str | None = None) -> dict:
    """
    Temporarily pause a mandate WITHOUT cancelling the underlying payment
    authorization. Scheduled payments will be skipped while paused. Use
    this whenever the user wants to "pause", "skip", "stop for now", or
    "hold off on" a recurring payment rather than cancel it outright.
    paused_until is an optional ISO date (YYYY-MM-DD); omit it to pause
    indefinitely until the user explicitly resumes.
    """

    def _run(db):
        mandate = MandateService.pause_mandate(
            db,
            uuid.UUID(mandate_id),
            paused_until=date.fromisoformat(paused_until) if paused_until else None,
            reason=reason,
        )
        return serialize_mandate(mandate)

    return run_with_session(_run)


@tool
def resume_mandate(mandate_id: str) -> dict:
    """
    Reactivate a paused mandate. No re-authorization is needed — the
    underlying payment authorization was never touched while paused.
    """

    def _run(db):
        mandate = MandateService.resume_mandate(db, uuid.UUID(mandate_id))
        return serialize_mandate(mandate)

    return run_with_session(_run)