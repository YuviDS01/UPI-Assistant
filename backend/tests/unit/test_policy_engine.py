"""
Policy engine tests. These are the exact scenarios from the spec (§4/§28):

    ₹1,299 groceries  -> allowed (limit 2000)
    ₹2,001 groceries  -> approval required
    ₹1,500 subscription -> allowed (limit 1500, boundary)
    ₹1,501 subscription -> approval required (just over boundary)
    ₹15,000 electronics -> approval required (no rule exists)

Each test creates and tears down its own user/rules — this suite must be
runnable independently of the seed script and independently of test order.
"""

import uuid
from datetime import date

import pytest

from app.models import Mandate, PaymentRule, User
from app.models.enums import MandateStatus
from app.policy.engine import PolicyEngine


@pytest.fixture
def policy_user(db_session):
    user = User(name="Policy Test User", email=f"policy-test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.flush()

    db_session.add_all(
        [
            PaymentRule(user_id=user.id, category="groceries", max_amount=2000, auto_approve=True),
            PaymentRule(user_id=user.id, category="subscriptions", max_amount=1500, auto_approve=True),
        ]
    )
    db_session.commit()

    yield user

    db_session.delete(user)  # cascades to payment_rules/mandates via ondelete=CASCADE
    db_session.commit()


@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine()


# ── Category policy (NEW_PAYMENT route) ──────────────────────────────────


def test_groceries_within_limit_is_allowed(db_session, policy_user, engine):
    result = engine.check_category_policy(db_session, policy_user.id, "groceries", 1299)
    assert result.allowed is True
    assert result.requires_approval is False


def test_groceries_over_limit_requires_approval(db_session, policy_user, engine):
    result = engine.check_category_policy(db_session, policy_user.id, "groceries", 2001)
    assert result.allowed is False
    assert result.requires_approval is True


def test_subscription_at_exact_boundary_is_allowed(db_session, policy_user, engine):
    result = engine.check_category_policy(db_session, policy_user.id, "subscriptions", 1500)
    assert result.allowed is True
    assert result.requires_approval is False


def test_subscription_just_over_boundary_requires_approval(db_session, policy_user, engine):
    result = engine.check_category_policy(db_session, policy_user.id, "subscriptions", 1501)
    assert result.allowed is False
    assert result.requires_approval is True


def test_category_with_no_rule_requires_approval(db_session, policy_user, engine):
    """This is the fail-closed guarantee: no rule => never auto-allow."""
    result = engine.check_category_policy(db_session, policy_user.id, "electronics", 15000)
    assert result.allowed is False
    assert result.requires_approval is True
    assert "no auto-approval rule" in result.reason.lower()


def test_rule_with_auto_approve_false_always_requires_approval(db_session, policy_user, engine):
    db_session.add(
        PaymentRule(user_id=policy_user.id, category="jewelry", max_amount=100000, auto_approve=False)
    )
    db_session.commit()

    result = engine.check_category_policy(db_session, policy_user.id, "jewelry", 1)
    assert result.allowed is False
    assert result.requires_approval is True


# ── Mandate execution policy (RECURRING_PAYMENT route) ───────────────────


def test_mandate_amount_within_limit_is_allowed(db_session, policy_user, engine):
    mandate = Mandate(
        user_id=policy_user.id,
        merchant_id="MERCH_TEST",
        merchant_name="Test Electricity Co",
        category="utilities",
        amount_limit=2500,
        frequency="MONTHLY",
        next_payment_date=date.today(),
        status=MandateStatus.ACTIVE,
    )
    db_session.add(mandate)
    db_session.commit()

    result = engine.check_mandate_execution(mandate, 2200)
    assert result.allowed is True
    assert result.requires_approval is False


def test_mandate_amount_over_limit_requires_approval(db_session, policy_user, engine):
    mandate = Mandate(
        user_id=policy_user.id,
        merchant_id="MERCH_TEST",
        merchant_name="Test Electricity Co",
        category="utilities",
        amount_limit=2500,
        frequency="MONTHLY",
        next_payment_date=date.today(),
        status=MandateStatus.ACTIVE,
    )
    db_session.add(mandate)
    db_session.commit()

    result = engine.check_mandate_execution(mandate, 3000)
    assert result.allowed is False
    assert result.requires_approval is True
