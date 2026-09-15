"""
The PaymentProvider interface. THIS is the seam that makes the provider
swappable (docs/architecture.md §10) — nothing above this line (LangGraph,
LangChain tools, PolicyEngine, services, the frontend) is allowed to know
whether it's talking to MockUPIProvider or PaytmSandboxProvider. They only
ever call these six methods.

Rules for any implementation:
  - Never move real money in a way that isn't explicitly gated by the
    caller having already passed policy + approval checks — the provider
    trusts its caller completely, which is exactly why PaymentService
    (Phase 6) is the only thing allowed to call it.
  - Every payment-executing method must be idempotent on idempotency_key:
    calling execute_payment twice with the same key must return the SAME
    result, never create a second payment.
  - Return values are plain Pydantic models, not provider-specific SDK
    objects — callers should never need to know which provider answered.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class ProviderMandateResult(BaseModel):
    provider_mandate_id: str
    status: str  # "ACTIVE" | "CANCELLED"


class ProviderPaymentResult(BaseModel):
    provider_transaction_id: str
    status: str  # "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED" | "CANCELLED"
    amount: float
    failure_reason: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    def create_mandate(
        self, user_reference: str, merchant_id: str, amount_limit: float, frequency: str
    ) -> ProviderMandateResult:
        """Register a new standing authorization with the provider."""

    @abstractmethod
    def cancel_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        """Terminal cancellation at the provider. Not used for pause — pause
        never calls the provider at all (see docs/architecture.md §0)."""

    @abstractmethod
    def get_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        """Fetch current provider-side status of a mandate."""

    @abstractmethod
    def execute_payment(
        self,
        idempotency_key: str,
        amount: float,
        merchant_id: str,
        mandate_provider_id: str | None = None,
    ) -> ProviderPaymentResult:
        """Attempt to move money. Must be idempotent on idempotency_key."""

    @abstractmethod
    def get_payment_status(self, provider_transaction_id: str) -> ProviderPaymentResult:
        """Poll for the current status of a previously-executed payment."""

    @abstractmethod
    def refund_payment(self, provider_transaction_id: str, amount: float) -> ProviderPaymentResult:
        """Reverse a previously successful payment, in part or in full."""