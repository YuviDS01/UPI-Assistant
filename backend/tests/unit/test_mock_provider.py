"""
MockUPIProvider tests. No DB, no network — pure in-memory behavior. Uses a
fresh provider instance per test (not the get_mock_provider() singleton) so
tests don't leak state into each other.
"""

from app.payment_providers.mock_provider import (
    MAGIC_FAILURE_AMOUNT,
    MAGIC_PENDING_AMOUNT,
    MockUPIProvider,
)


def test_create_mandate_returns_active_with_mock_prefixed_id():
    provider = MockUPIProvider()
    result = provider.create_mandate("user-1", "MERCH_1", amount_limit=2500, frequency="MONTHLY")
    assert result.status == "ACTIVE"
    assert result.provider_mandate_id.startswith("MOCK_MANDATE_")


def test_cancel_mandate_returns_cancelled():
    provider = MockUPIProvider()
    created = provider.create_mandate("user-1", "MERCH_1", amount_limit=2500, frequency="MONTHLY")
    cancelled = provider.cancel_mandate(created.provider_mandate_id)
    assert cancelled.status == "CANCELLED"
    assert cancelled.provider_mandate_id == created.provider_mandate_id


def test_get_mandate_reflects_latest_status():
    provider = MockUPIProvider()
    created = provider.create_mandate("user-1", "MERCH_1", amount_limit=2500, frequency="MONTHLY")
    provider.cancel_mandate(created.provider_mandate_id)
    fetched = provider.get_mandate(created.provider_mandate_id)
    assert fetched.status == "CANCELLED"


def test_execute_payment_normal_amount_succeeds():
    provider = MockUPIProvider()
    result = provider.execute_payment(idempotency_key="key-1", amount=1299, merchant_id="MERCH_1")
    assert result.status == "SUCCESS"
    assert result.provider_transaction_id.startswith("MOCK_TXN_")
    assert result.failure_reason is None


def test_execute_payment_magic_amount_simulates_failure():
    provider = MockUPIProvider()
    result = provider.execute_payment(
        idempotency_key="key-2", amount=MAGIC_FAILURE_AMOUNT, merchant_id="MERCH_1"
    )
    assert result.status == "FAILED"
    assert result.failure_reason is not None


def test_execute_payment_magic_amount_simulates_pending():
    provider = MockUPIProvider()
    result = provider.execute_payment(
        idempotency_key="key-3", amount=MAGIC_PENDING_AMOUNT, merchant_id="MERCH_1"
    )
    assert result.status == "PENDING"


def test_execute_payment_is_idempotent_on_key():
    """Same idempotency_key called twice must return the SAME transaction,
    not create a second one — this is Test 6 from the spec (§28)."""
    provider = MockUPIProvider()
    first = provider.execute_payment(idempotency_key="dup-key", amount=500, merchant_id="MERCH_1")
    second = provider.execute_payment(idempotency_key="dup-key", amount=500, merchant_id="MERCH_1")
    assert first.provider_transaction_id == second.provider_transaction_id


def test_get_payment_status_matches_execution_result():
    provider = MockUPIProvider()
    executed = provider.execute_payment(idempotency_key="key-4", amount=1000, merchant_id="MERCH_1")
    status = provider.get_payment_status(executed.provider_transaction_id)
    assert status.status == executed.status
    assert status.provider_transaction_id == executed.provider_transaction_id


def test_get_payment_status_for_unknown_transaction_reports_failed():
    provider = MockUPIProvider()
    status = provider.get_payment_status("MOCK_TXN_DOES_NOT_EXIST")
    assert status.status == "FAILED"


def test_refund_successful_payment_succeeds():
    provider = MockUPIProvider()
    executed = provider.execute_payment(idempotency_key="key-5", amount=1000, merchant_id="MERCH_1")
    refund = provider.refund_payment(executed.provider_transaction_id, amount=1000)
    assert refund.status == "SUCCESS"


def test_refund_failed_payment_is_rejected():
    provider = MockUPIProvider()
    executed = provider.execute_payment(
        idempotency_key="key-6", amount=MAGIC_FAILURE_AMOUNT, merchant_id="MERCH_1"
    )
    refund = provider.refund_payment(executed.provider_transaction_id, amount=MAGIC_FAILURE_AMOUNT)
    assert refund.status == "FAILED"