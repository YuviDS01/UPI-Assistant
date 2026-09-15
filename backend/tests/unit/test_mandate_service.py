import uuid
from datetime import date, timedelta

import pytest

from app.core.exceptions import MandateNotFoundError, MandateStateError
from app.models import Mandate, User
from app.models.enums import MandateStatus
from app.services.mandate_service import MandateService, compute_next_payment_date


@pytest.fixture
def user(db_session):
    u = User(name="Mandate Test User", email=f"mandate-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def test_create_mandate_is_active(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Electricity Co", "utilities", 2500, "MONTHLY", date.today()
    )
    assert mandate.status == MandateStatus.ACTIVE


def test_pause_mandate_does_not_touch_provider_mandate_id(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Electricity Co", "utilities", 2500, "MONTHLY",
        date.today(), provider_mandate_id="MOCK_MANDATE_ABC123",
    )
    paused = MandateService.pause_mandate(
        db_session, mandate.id, paused_until=date.today() + timedelta(days=60), reason="Not using the app"
    )
    assert paused.status == MandateStatus.PAUSED
    assert paused.provider_mandate_id == "MOCK_MANDATE_ABC123"  # untouched — the whole point of the USP


def test_pause_indefinitely_with_null_until(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Streaming Co", "subscriptions", 999, "MONTHLY", date.today()
    )
    paused = MandateService.pause_mandate(db_session, mandate.id, paused_until=None, reason="Taking a break")
    assert paused.status == MandateStatus.PAUSED
    assert paused.paused_until is None


def test_resume_reactivates_and_recomputes_next_payment_date(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Streaming Co", "subscriptions", 999, "MONTHLY", date.today()
    )
    MandateService.pause_mandate(db_session, mandate.id, paused_until=None)
    resumed = MandateService.resume_mandate(db_session, mandate.id)
    assert resumed.status == MandateStatus.ACTIVE
    assert resumed.paused_until is None
    assert resumed.next_payment_date > date.today()


def test_cannot_pause_a_cancelled_mandate(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Streaming Co", "subscriptions", 999, "MONTHLY", date.today()
    )
    MandateService.cancel_mandate(db_session, mandate.id)
    with pytest.raises(MandateStateError):
        MandateService.pause_mandate(db_session, mandate.id)


def test_cannot_resume_a_mandate_that_is_not_paused(db_session, user):
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_1", "Streaming Co", "subscriptions", 999, "MONTHLY", date.today()
    )
    with pytest.raises(MandateStateError):
        MandateService.resume_mandate(db_session, mandate.id)


def test_get_mandate_raises_not_found_for_unknown_id(db_session):
    with pytest.raises(MandateNotFoundError):
        MandateService.get_mandate(db_session, uuid.uuid4())


def test_check_can_execute_active_mandate():
    mandate = Mandate(status=MandateStatus.ACTIVE, paused_until=None)
    decision = MandateService.check_can_execute(mandate)
    assert decision.should_execute is True


def test_check_can_execute_paused_mandate_indefinite():
    mandate = Mandate(status=MandateStatus.PAUSED, paused_until=None)
    decision = MandateService.check_can_execute(mandate)
    assert decision.should_execute is False
    assert "paused" in decision.skip_reason.lower()


def test_check_can_execute_paused_mandate_still_in_window():
    mandate = Mandate(status=MandateStatus.PAUSED, paused_until=date.today() + timedelta(days=10))
    decision = MandateService.check_can_execute(mandate)
    assert decision.should_execute is False


def test_check_can_execute_cancelled_mandate():
    mandate = Mandate(status=MandateStatus.CANCELLED)
    decision = MandateService.check_can_execute(mandate)
    assert decision.should_execute is False


def test_compute_next_payment_date_monthly_handles_month_end():
    result = compute_next_payment_date("MONTHLY", from_date=date(2026, 1, 31))
    assert result == date(2026, 2, 28)  # Feb has no 31st, must clamp not crash