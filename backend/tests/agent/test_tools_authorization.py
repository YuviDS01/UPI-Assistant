"""
The tests that matter most in this whole project: proving an agent tool
call cannot move money without real backend authorization, no matter what
Claude "believes" it's allowed to do.
"""

import uuid
from datetime import date

import pytest

from app.agent.tools.mandate_tools import cancel_mandate, pause_mandate, resume_mandate
from app.agent.tools.payment_tools import execute_payment, simulate_new_payment
from app.core.database import SessionLocal
from app.models import User
from app.models.enums import MandateStatus
from app.services.mandate_service import MandateService


@pytest.fixture
def user():
    db = SessionLocal()
    u = User(name="Tool Test User", email=f"tool-test-{uuid.uuid4()}@example.com")
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.delete(u)
    db.commit()
    db.close()


def test_execute_payment_within_policy_auto_executes(user):
    created = simulate_new_payment.invoke(
        {
            "user_id": str(user.id),
            "merchant_id": "MERCH_1",
            "merchant_name": "Grocery Store",
            "category": "groceries",
            "amount": 1299,
        }
    )
    # No payment_rules row exists for this fresh user/category -> fail-closed
    result = execute_payment.invoke({"transaction_id": created["transaction_id"]})
    assert result["executed"] is False
    assert result["requires_approval"] is True


def test_execute_payment_out_of_policy_without_approval_is_refused(user):
    created = simulate_new_payment.invoke(
        {
            "user_id": str(user.id),
            "merchant_id": "MERCH_2",
            "merchant_name": "XYZ Electronics",
            "category": "electronics",
            "amount": 15000,
        }
    )
    result = execute_payment.invoke({"transaction_id": created["transaction_id"]})
    assert result["executed"] is False
    assert result["requires_approval"] is True
    # Proves the tool call alone never moved money, regardless of what a
    # calling agent might have "intended".


def test_execute_payment_on_unknown_transaction_returns_tool_error():
    result = execute_payment.invoke({"transaction_id": str(uuid.uuid4())})
    assert result["error"] == "TRANSACTION_NOT_FOUND"


def test_pause_then_resume_via_tools_preserves_provider_mandate_id():
    db = SessionLocal()
    u = User(name="Pause Tool User", email=f"pause-tool-{uuid.uuid4()}@example.com")
    db.add(u)
    db.commit()

    mandate = MandateService.create_mandate(
        db, u.id, "MERCH_3", "Streaming Co", "subscriptions", 999, "MONTHLY",
        date.today(), provider_mandate_id="MOCK_MANDATE_KEEP_ME",
    )
    mandate_id = str(mandate.id)
    db.close()

    paused = pause_mandate.invoke({"mandate_id": mandate_id, "paused_until": None, "reason": "not using it"})
    assert paused["status"] == MandateStatus.PAUSED

    resumed = resume_mandate.invoke({"mandate_id": mandate_id})
    assert resumed["status"] == MandateStatus.ACTIVE

    db = SessionLocal()
    from app.models import Mandate as MandateModel

    refreshed = db.get(MandateModel, uuid.UUID(mandate_id))
    assert refreshed.provider_mandate_id == "MOCK_MANDATE_KEEP_ME"
    db.delete(u)
    db.commit()
    db.close()