import uuid

import pytest

from app.core.exceptions import PolicyViolationError
from app.models import Transaction, User
from app.models.enums import PaymentType, TransactionStatus
from app.payment_providers.mock_provider import MAGIC_FAILURE_AMOUNT, MockUPIProvider
from app.services.payment_service import PaymentService
from app.services.transaction_service import TransactionService


@pytest.fixture
def user(db_session):
    u = User(name="Payment Test User", email=f"payment-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def _make_transaction(db_session, user, amount, idempotency_key) -> Transaction:
    txn, _ = TransactionService.get_or_create(
        db_session, user_id=user.id, idempotency_key=idempotency_key,
        merchant_id="MERCH_1", merchant_name="Test Merchant", category="groceries",
        amount=amount, payment_type=PaymentType.NEW,
    )
    db_session.commit()
    return txn


def test_execute_payment_requires_valid_authorization_source(db_session, user):
    txn = _make_transaction(db_session, user, 1299, f"key-{uuid.uuid4()}")
    provider = MockUPIProvider()
    with pytest.raises(PolicyViolationError):
        PaymentService.execute_payment_authorized(db_session, txn, provider, authorization_source="i_made_this_up")


def test_execute_payment_succeeds_with_valid_authorization(db_session, user):
    txn = _make_transaction(db_session, user, 1299, f"key-{uuid.uuid4()}")
    provider = MockUPIProvider()
    result = PaymentService.execute_payment_authorized(
        db_session, txn, provider, authorization_source="policy_auto_approved"
    )
    assert result.status == TransactionStatus.SUCCESS
    assert result.provider_transaction_id is not None


def test_execute_payment_records_failure_reason_on_provider_failure(db_session, user):
    txn = _make_transaction(db_session, user, MAGIC_FAILURE_AMOUNT, f"key-{uuid.uuid4()}")
    provider = MockUPIProvider()
    result = PaymentService.execute_payment_authorized(
        db_session, txn, provider, authorization_source="human_approved"
    )
    assert result.status == TransactionStatus.FAILED
    assert result.failure_reason is not None


def test_executing_an_already_terminal_transaction_is_a_safe_no_op(db_session, user):
    """Calling execute twice on the same already-SUCCESS transaction must
    not create a second charge — the DB-level idempotency guarantee."""
    txn = _make_transaction(db_session, user, 500, f"key-{uuid.uuid4()}")
    provider = MockUPIProvider()
    first = PaymentService.execute_payment_authorized(
        db_session, txn, provider, authorization_source="policy_auto_approved"
    )
    first_provider_txn_id = first.provider_transaction_id

    second = PaymentService.execute_payment_authorized(
        db_session, txn, provider, authorization_source="policy_auto_approved"
    )
    assert second.provider_transaction_id == first_provider_txn_id


def test_duplicate_idempotency_key_returns_same_transaction_row(db_session, user):
    key = f"key-{uuid.uuid4()}"
    txn1, created1 = TransactionService.get_or_create(
        db_session, user_id=user.id, idempotency_key=key, merchant_id="MERCH_1",
        merchant_name="Test Merchant", category="groceries", amount=500, payment_type=PaymentType.NEW,
    )
    db_session.commit()
    txn2, created2 = TransactionService.get_or_create(
        db_session, user_id=user.id, idempotency_key=key, merchant_id="MERCH_1",
        merchant_name="Test Merchant", category="groceries", amount=500, payment_type=PaymentType.NEW,
    )
    assert created1 is True
    assert created2 is False
    assert txn1.id == txn2.id