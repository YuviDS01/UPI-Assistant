"""
The recurring-payment job. Runs on a timer via SchedulerService.

Path is deliberately: Scheduler -> TransactionService -> PaymentService ->
PolicyEngine -> PaymentProvider — same as docs/architecture.md §17. The
scheduler NEVER calls PaymentProvider directly.

This is also where the pause/resume USP pays off automatically: a mandate
that's PAUSED gets caught by MandateService.check_can_execute and skipped
before any policy check or provider call happens — no chat message, no
human involved, just a silent (but fully audited) no-op.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Mandate
from app.models.enums import MandateStatus, PaymentType
from app.payment_providers.factory import get_payment_provider
from app.services.audit_service import AuditService
from app.services.mandate_service import MandateService, compute_next_payment_date
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.services.transaction_service import TransactionService

logger = logging.getLogger("app.scheduler")


def _handle_skip(db: Session, mandate: Mandate) -> None:
    decision = MandateService.check_can_execute(mandate)
    event_type = "PAYMENT_SKIPPED_PAUSED" if mandate.status == MandateStatus.PAUSED else "PAYMENT_SKIPPED"

    AuditService.log_event(
        db, event_type, "mandate", mandate.id, user_id=mandate.user_id, reason=decision.skip_reason
    )
    NotificationService.notify(
        db,
        mandate.user_id,
        title="Scheduled payment skipped",
        body=f"Your {mandate.frequency.lower()} payment to {mandate.merchant_name} was skipped: {decision.skip_reason}",
    )
    # Advance the date even while skipped, so a paused mandate is re-checked
    # next cycle instead of being flagged as "due" every scheduler tick.
    mandate.next_payment_date = compute_next_payment_date(mandate.frequency, from_date=mandate.next_payment_date)
    db.commit()


def _handle_execute(db: Session, mandate: Mandate) -> None:
    provider = get_payment_provider()
    idempotency_key = f"recurring-{mandate.id}-{mandate.next_payment_date.isoformat()}"

    txn, _ = TransactionService.get_or_create(
        db,
        user_id=mandate.user_id,
        idempotency_key=idempotency_key,
        merchant_id=mandate.merchant_id,
        merchant_name=mandate.merchant_name,
        category=mandate.category,
        amount=float(mandate.amount_limit),
        payment_type=PaymentType.RECURRING,
        mandate_id=mandate.id,
    )
    db.commit()

    PaymentService.authorize_and_execute(db, txn, provider, mandate=mandate)

    # Advance regardless of SUCCESS/FAILED — a failed charge doesn't retry
    # every tick; it surfaces via the notification and payment history, and
    # the next attempt happens on the mandate's normal next cycle.
    mandate.next_payment_date = compute_next_payment_date(mandate.frequency, from_date=mandate.next_payment_date)
    db.commit()


def process_due_mandates(db_session_factory=SessionLocal) -> int:
    """
    Finds every ACTIVE or PAUSED mandate whose next_payment_date has
    arrived, and processes each one exactly once. Returns the count
    processed (used by tests and logging — not by the scheduler itself).
    """
    db = db_session_factory()
    processed = 0
    try:
        due_mandates = (
            db.query(Mandate)
            .filter(
                Mandate.status.in_([MandateStatus.ACTIVE, MandateStatus.PAUSED]),
                Mandate.next_payment_date <= date.today(),
            )
            .all()
        )

        for mandate in due_mandates:
            decision = MandateService.check_can_execute(mandate)
            try:
                if decision.should_execute:
                    _handle_execute(db, mandate)
                else:
                    _handle_skip(db, mandate)
            except Exception:
                db.rollback()
                logger.exception(f"Scheduler failed processing mandate {mandate.id}")
                continue
            processed += 1

        return processed
    finally:
        db.close()