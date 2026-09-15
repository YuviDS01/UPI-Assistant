"""
Read-only agent tools: mandates, upcoming payments, payment history,
notifications. These never modify state — safe for Claude to call freely
while gathering context, without any policy or approval concern.
"""

import uuid
from datetime import date, timedelta

from langchain_core.tools import tool
from sqlalchemy import and_

from app.agent.tools._common import run_with_session, serialize_mandate, serialize_transaction
from app.models import Mandate, Notification, Transaction
from app.models.enums import MandateStatus


@tool
def get_mandates(user_id: str) -> list[dict]:
    """List all of a user's mandates (any status)."""

    def _run(db):
        mandates = db.query(Mandate).filter(Mandate.user_id == uuid.UUID(user_id)).all()
        return [serialize_mandate(m) for m in mandates]

    return run_with_session(_run)


@tool
def get_upcoming_payments(user_id: str, days_ahead: int = 30) -> list[dict]:
    """List ACTIVE mandates whose next_payment_date falls within the next
    `days_ahead` days. Paused/cancelled/expired mandates are excluded since
    they won't actually charge."""

    def _run(db):
        cutoff = date.today() + timedelta(days=days_ahead)
        mandates = (
            db.query(Mandate)
            .filter(
                and_(
                    Mandate.user_id == uuid.UUID(user_id),
                    Mandate.status == MandateStatus.ACTIVE,
                    Mandate.next_payment_date <= cutoff,
                )
            )
            .order_by(Mandate.next_payment_date)
            .all()
        )
        return [serialize_mandate(m) for m in mandates]

    return run_with_session(_run)


@tool
def get_payment_history(user_id: str, limit: int = 20) -> list[dict]:
    """List a user's past transactions, most recent first."""

    def _run(db):
        txns = (
            db.query(Transaction)
            .filter(Transaction.user_id == uuid.UUID(user_id))
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [serialize_transaction(t) for t in txns]

    return run_with_session(_run)


@tool
def get_notifications(user_id: str, limit: int = 10) -> list[dict]:
    """List a user's recent notifications, most recent first. Use this to
    relay what actually happened — never invent a notification's content."""

    def _run(db):
        notes = (
            db.query(Notification)
            .filter(Notification.user_id == uuid.UUID(user_id))
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"title": n.title, "body": n.body, "created_at": n.created_at.isoformat()} for n in notes]

    return run_with_session(_run)