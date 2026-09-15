"""
MandateService: create/cancel/pause/resume, and the deterministic check the
scheduler (Phase 10) will use to decide whether a due mandate actually runs.

pause_mandate / resume_mandate are the USP (docs/architecture.md §0):
pausing NEVER touches provider_mandate_id or calls the PaymentProvider —
the standing bank-side authorization is left completely alone. Only our own
`status` column changes, which is exactly why resuming needs no
re-authorization.
"""

import calendar
import uuid
from datetime import date

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import MandateNotFoundError, MandateStateError
from app.models import Mandate
from app.models.enums import MandateStatus
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

FREQUENCY_STEPS = {
    "DAILY": ("days", 1),
    "WEEKLY": ("days", 7),
    "MONTHLY": ("months", 1),
    "YEARLY": ("months", 12),
}


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def compute_next_payment_date(frequency: str, from_date: date | None = None) -> date:
    from_date = from_date or date.today()
    unit, amount = FREQUENCY_STEPS.get(frequency.upper(), ("months", 1))
    if unit == "days":
        from datetime import timedelta

        return from_date + timedelta(days=amount)
    return _add_months(from_date, amount)


class MandateExecutionDecision(BaseModel):
    should_execute: bool
    skip_reason: str | None = None


class MandateService:
    @staticmethod
    def get_mandate(db: Session, mandate_id: uuid.UUID) -> Mandate:
        mandate = db.get(Mandate, mandate_id)
        if mandate is None:
            raise MandateNotFoundError(f"No mandate found for id {mandate_id}.")
        return mandate

    @staticmethod
    def create_mandate(
        db: Session,
        user_id: uuid.UUID,
        merchant_id: str,
        merchant_name: str,
        category: str,
        amount_limit: float,
        frequency: str,
        next_payment_date: date,
        provider_mandate_id: str | None = None,
    ) -> Mandate:
        mandate = Mandate(
            user_id=user_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            amount_limit=amount_limit,
            frequency=frequency,
            next_payment_date=next_payment_date,
            status=MandateStatus.ACTIVE,
            provider_mandate_id=provider_mandate_id,
        )
        db.add(mandate)
        db.flush()
        AuditService.log_event(
            db, "MANDATE_CREATED", "mandate", mandate.id, user_id=user_id,
            metadata={"merchant_name": merchant_name, "amount_limit": amount_limit, "frequency": frequency},
        )
        NotificationService.notify(
            db, user_id, title="Mandate created",
            body=f"Recurring payment to {merchant_name} set up, up to ₹{amount_limit} {frequency.lower()}.",
        )
        db.commit()
        db.refresh(mandate)
        return mandate

    @staticmethod
    def cancel_mandate(db: Session, mandate_id: uuid.UUID) -> Mandate:
        mandate = MandateService.get_mandate(db, mandate_id)
        if mandate.status in (MandateStatus.CANCELLED, MandateStatus.EXPIRED):
            raise MandateStateError(f"Mandate {mandate_id} is already {mandate.status} — cannot cancel again.")

        mandate.status = MandateStatus.CANCELLED
        db.flush()
        AuditService.log_event(db, "MANDATE_CANCELLED", "mandate", mandate.id, user_id=mandate.user_id)
        NotificationService.notify(
            db, mandate.user_id, title="Mandate cancelled",
            body=f"Recurring payment to {mandate.merchant_name} has been cancelled.",
        )
        db.commit()
        db.refresh(mandate)
        return mandate

    @staticmethod
    def pause_mandate(
        db: Session, mandate_id: uuid.UUID, paused_until: date | None = None, reason: str | None = None
    ) -> Mandate:
        """
        THE USP. paused_until=None means "pause indefinitely, until the user
        explicitly resumes." Never touches provider_mandate_id.
        """
        mandate = MandateService.get_mandate(db, mandate_id)
        if mandate.status in (MandateStatus.CANCELLED, MandateStatus.EXPIRED):
            raise MandateStateError(
                f"Mandate {mandate_id} is {mandate.status} — cannot pause a terminal mandate."
            )

        mandate.status = MandateStatus.PAUSED
        mandate.paused_until = paused_until
        mandate.pause_reason = reason
        db.flush()

        AuditService.log_event(
            db, "MANDATE_PAUSED", "mandate", mandate.id, user_id=mandate.user_id, reason=reason,
            metadata={"paused_until": paused_until.isoformat() if paused_until else None},
        )
        until_text = f"until {paused_until.isoformat()}" if paused_until else "until you resume it"
        NotificationService.notify(
            db, mandate.user_id, title="Mandate paused",
            body=f"Payments to {mandate.merchant_name} are paused {until_text}. Your mandate stays active — no re-authorization needed when you resume.",
        )
        db.commit()
        db.refresh(mandate)
        return mandate

    @staticmethod
    def resume_mandate(db: Session, mandate_id: uuid.UUID) -> Mandate:
        mandate = MandateService.get_mandate(db, mandate_id)
        if mandate.status != MandateStatus.PAUSED:
            raise MandateStateError(f"Mandate {mandate_id} is {mandate.status}, not PAUSED — nothing to resume.")

        mandate.status = MandateStatus.ACTIVE
        mandate.paused_until = None
        mandate.pause_reason = None
        mandate.next_payment_date = compute_next_payment_date(mandate.frequency, from_date=date.today())
        db.flush()

        AuditService.log_event(db, "MANDATE_RESUMED", "mandate", mandate.id, user_id=mandate.user_id)
        NotificationService.notify(
            db, mandate.user_id, title="Mandate resumed",
            body=f"Payments to {mandate.merchant_name} have resumed. Next payment: {mandate.next_payment_date}.",
        )
        db.commit()
        db.refresh(mandate)
        return mandate

    @staticmethod
    def check_can_execute(mandate: Mandate) -> MandateExecutionDecision:
        """
        Deterministic pre-flight check used by the scheduler (Phase 10)
        before it even calls the policy engine. This is what makes the
        USP real at execution time, not just at pause time.
        """
        if mandate.status == MandateStatus.CANCELLED:
            return MandateExecutionDecision(should_execute=False, skip_reason="Mandate is cancelled.")
        if mandate.status == MandateStatus.EXPIRED:
            return MandateExecutionDecision(should_execute=False, skip_reason="Mandate is expired.")
        if mandate.status == MandateStatus.PAUSED:
            if mandate.paused_until is None or mandate.paused_until >= date.today():
                return MandateExecutionDecision(should_execute=False, skip_reason="Mandate is paused.")
            return MandateExecutionDecision(
                should_execute=False,
                skip_reason="Pause period has ended but mandate has not been explicitly resumed.",
            )
        if mandate.status == MandateStatus.ACTIVE:
            return MandateExecutionDecision(should_execute=True)
        return MandateExecutionDecision(should_execute=False, skip_reason=f"Unhandled status {mandate.status}.")