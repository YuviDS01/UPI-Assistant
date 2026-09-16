"""
Scheduler tests, calling process_due_mandates() directly as a plain
function rather than waiting on a real timer. Covers spec Test 7 (a due
recurring mandate executes end-to-end) and the pause USP's actual payoff:
a due, paused mandate is skipped with zero manual intervention.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models import Mandate, Transaction, User
from app.models.enums import MandateStatus, TransactionStatus
from app.services.mandate_service import MandateService
from app.workers.payment_scheduler import process_due_mandates


@pytest.fixture
def user(db_session):
    u = User(name="Scheduler Test User", email=f"scheduler-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def test_due_active_mandate_executes_and_advances_date(db_session, user):
    """Spec Test 7: mandate due -> scheduler -> policy -> payment -> status -> notification."""
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Electricity Co", "utilities", 2500, "MONTHLY", date.today()
    )

    processed = process_due_mandates()
    assert processed >= 1

    db_session.refresh(mandate)
    assert mandate.next_payment_date > date.today()

    txn = (
        db_session.query(Transaction)
        .filter(Transaction.mandate_id == mandate.id)
        .order_by(Transaction.created_at.desc())
        .first()
    )
    assert txn is not None
    assert txn.status == TransactionStatus.SUCCESS


def test_due_paused_mandate_is_skipped_not_charged(db_session, user):
    """
    THE USP, proven end to end: a due mandate that's paused produces no
    transaction at all — the scheduler silently skips it, still advances
    next_payment_date so it's re-checked next cycle, and the underlying
    provider_mandate_id is never touched.
    """
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_2", "Streaming Co", "subscriptions", 649, "MONTHLY",
        date.today(), provider_mandate_id="MOCK_MANDATE_KEEP_ME",
    )
    MandateService.pause_mandate(db_session, mandate.id, paused_until=None, reason="not using it")

    process_due_mandates()

    db_session.refresh(mandate)
    assert mandate.status == MandateStatus.PAUSED
    assert mandate.provider_mandate_id == "MOCK_MANDATE_KEEP_ME"  # untouched
    assert mandate.next_payment_date > date.today()  # re-checked next cycle, not stuck

    txn_count = db_session.query(Transaction).filter(Transaction.mandate_id == mandate.id).count()
    assert txn_count == 0  # no money moved, no transaction created at all


def test_cancelled_mandate_is_never_processed(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_3", "Old Gym", "subscriptions", 1200, "MONTHLY", date.today()
    )
    MandateService.cancel_mandate(db_session, mandate.id)
    original_date = mandate.next_payment_date

    process_due_mandates()

    db_session.refresh(mandate)
    assert mandate.next_payment_date == original_date  # scheduler query excludes CANCELLED entirely
    assert db_session.query(Transaction).filter(Transaction.mandate_id == mandate.id).count() == 0


def test_not_yet_due_mandate_is_left_alone(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_4", "Future Co", "subscriptions", 500, "MONTHLY",
        date.today() + timedelta(days=15),
    )
    process_due_mandates()

    db_session.refresh(mandate)
    assert db_session.query(Transaction).filter(Transaction.mandate_id == mandate.id).count() == 0