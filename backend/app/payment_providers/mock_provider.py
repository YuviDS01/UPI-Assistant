"""
MockUPIProvider - the default provider for this prototype. Fully local,
no network calls, no real money ever moves. Deterministic so demos and
tests are repeatable: specific "magic" amounts simulate failure/pending so
you can exercise those code paths on purpose without needing a real
provider sandbox.

State is held in-memory (two dicts) and is intentionally per-process, not
per-request — get a shared instance via get_mock_provider() so a payment
executed in one request can have its status polled in another. This is a
deliberate prototype simplification: state resets on restart, and there is
no multi-process fan-out. A real provider (PaytmSandboxProvider) has none
of these limitations because the provider itself is the source of truth,
not this process's memory.
"""

import uuid
from functools import lru_cache

from app.payment_providers.base import PaymentProvider, ProviderMandateResult, ProviderPaymentResult

# Magic amounts for deterministic demo/test scenarios — documented here so
# nobody has to reverse-engineer why a specific number "fails".
MAGIC_FAILURE_AMOUNT = 66666.0
MAGIC_PENDING_AMOUNT = 77777.0


class MockUPIProvider(PaymentProvider):
    def __init__(self) -> None:
        self._mandates: dict[str, ProviderMandateResult] = {}
        # idempotency_key -> ProviderPaymentResult (keyed by OUR idempotency
        # key, not the provider transaction id, so repeat calls are caught)
        self._payments_by_idempotency_key: dict[str, ProviderPaymentResult] = {}
        self._payments_by_transaction_id: dict[str, ProviderPaymentResult] = {}

    def create_mandate(
        self, user_reference: str, merchant_id: str, amount_limit: float, frequency: str
    ) -> ProviderMandateResult:
        provider_mandate_id = f"MOCK_MANDATE_{uuid.uuid4().hex[:12].upper()}"
        result = ProviderMandateResult(provider_mandate_id=provider_mandate_id, status="ACTIVE")
        self._mandates[provider_mandate_id] = result
        return result

    def cancel_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        result = ProviderMandateResult(provider_mandate_id=provider_mandate_id, status="CANCELLED")
        self._mandates[provider_mandate_id] = result
        return result

    def get_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        existing = self._mandates.get(provider_mandate_id)
        if existing is not None:
            return existing
        # Unknown id: report it as cancelled rather than raising, so callers
        # get a safe, explicit answer instead of an exception mid-workflow.
        return ProviderMandateResult(provider_mandate_id=provider_mandate_id, status="CANCELLED")

    def execute_payment(
        self,
        idempotency_key: str,
        amount: float,
        merchant_id: str,
        mandate_provider_id: str | None = None,
    ) -> ProviderPaymentResult:
        # Idempotency, enforced at the provider level too (defense in depth
        # — PaymentService/DB unique constraint enforce it as well, Phase 6).
        cached = self._payments_by_idempotency_key.get(idempotency_key)
        if cached is not None:
            return cached

        provider_transaction_id = f"MOCK_TXN_{uuid.uuid4().hex[:12].upper()}"

        if amount == MAGIC_FAILURE_AMOUNT:
            result = ProviderPaymentResult(
                provider_transaction_id=provider_transaction_id,
                status="FAILED",
                amount=amount,
                failure_reason="Simulated failure (magic test amount 66666).",
            )
        elif amount == MAGIC_PENDING_AMOUNT:
            result = ProviderPaymentResult(
                provider_transaction_id=provider_transaction_id, status="PENDING", amount=amount
            )
        else:
            result = ProviderPaymentResult(
                provider_transaction_id=provider_transaction_id, status="SUCCESS", amount=amount
            )

        self._payments_by_idempotency_key[idempotency_key] = result
        self._payments_by_transaction_id[provider_transaction_id] = result
        return result

    def get_payment_status(self, provider_transaction_id: str) -> ProviderPaymentResult:
        existing = self._payments_by_transaction_id.get(provider_transaction_id)
        if existing is not None:
            return existing
        return ProviderPaymentResult(
            provider_transaction_id=provider_transaction_id,
            status="FAILED",
            amount=0.0,
            failure_reason="Unknown transaction id.",
        )

    def refund_payment(self, provider_transaction_id: str, amount: float) -> ProviderPaymentResult:
        original = self._payments_by_transaction_id.get(provider_transaction_id)
        if original is None or original.status != "SUCCESS":
            return ProviderPaymentResult(
                provider_transaction_id=provider_transaction_id,
                status="FAILED",
                amount=amount,
                failure_reason="Cannot refund a transaction that was not successful.",
            )
        return ProviderPaymentResult(
            provider_transaction_id=provider_transaction_id, status="SUCCESS", amount=amount
        )


@lru_cache
def get_mock_provider() -> MockUPIProvider:
    """Process-wide singleton so execute_payment and get_payment_status see
    the same in-memory state across requests within one running process."""
    return MockUPIProvider()