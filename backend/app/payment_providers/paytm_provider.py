"""
PaytmSandboxProvider — implements the same PaymentProvider interface as
MockUPIProvider (Phase 5). See this module's TODOs and paytm_checksum.py
before treating this as production-ready; it's a structural scaffold, not
a verified integration (no real sandbox credentials were available to
test against while building this).

Key behavioral difference from MockUPIProvider that matters architecturally:
create_mandate here CANNOT return "ACTIVE" synchronously — a real UPI
mandate requires the customer to approve it in their UPI app first. This
provider returns "PENDING" and the caller (MandateService, Phase 6) would
need a way to poll get_mandate() or receive a callback before treating the
mandate as usable. Nothing in MandateService currently does that polling —
that's explicitly flagged as a gap here rather than silently glossed over.
"""

import uuid

import httpx

from app.core.config import get_settings
from app.payment_providers.base import PaymentProvider, ProviderMandateResult, ProviderPaymentResult
from app.payment_providers.paytm_checksum import generate_signature


class PaytmSandboxProvider(PaymentProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.paytm_mid or not settings.paytm_merchant_key:
            raise NotImplementedError(
                "PAYTM_MID and PAYTM_MERCHANT_KEY must be set in .env before "
                "PaytmSandboxProvider can be used. Set PAYMENT_PROVIDER=mock "
                "to keep using the demo provider in the meantime."
            )
        self._settings = settings
        self._client = httpx.Client(base_url=settings.paytm_base_url, timeout=15.0)

    def _signed_request(self, path: str, body: dict) -> dict:
        payload = {
            "head": {
                "channelId": "WEB",
                "signature": generate_signature(body, self._settings.paytm_merchant_key),
            },
            "body": body,
        }
        response = self._client.post(path, json=payload)
        response.raise_for_status()
        return response.json()

    def create_mandate(
        self, user_reference: str, merchant_id: str, amount_limit: float, frequency: str
    ) -> ProviderMandateResult:
        # Endpoint/fields per business.paytm.com/docs/api/subscription (create).
        # subscriptionFrequencyUnit expects DAY/MONTH/YEAR-style values in
        # Paytm's real API — mapped from our internal DAILY/MONTHLY/YEARLY.
        unit_map = {"DAILY": "DAY", "WEEKLY": "DAY", "MONTHLY": "MONTH", "YEARLY": "YEAR"}
        order_id = f"ORDER_{uuid.uuid4().hex[:16].upper()}"

        body = {
            "mid": self._settings.paytm_mid,
            "requestType": "SUBSCRIPTION",
            "orderId": order_id,
            "subscriptionAmountType": "VARIABLE",
            "subscriptionMaxAmount": str(amount_limit),
            "subscriptionFrequency": "1",
            "subscriptionFrequencyUnit": unit_map.get(frequency.upper(), "MONTH"),
            "userInfo": {"custId": user_reference},
        }

        response = self._signed_request("/aoa-subscription/api/v2/subscription/create", body)

        # Real response requires the customer to approve in their UPI app
        # before the mandate is truly ACTIVE — report PENDING honestly.
        subscription_id = response.get("body", {}).get("subscriptionId", order_id)
        return ProviderMandateResult(provider_mandate_id=subscription_id, status="PENDING")

    def cancel_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        body = {"mid": self._settings.paytm_mid, "subscriptionId": provider_mandate_id}
        self._signed_request("/aoa-subscription/api/v2/subscription/cancel", body)
        return ProviderMandateResult(provider_mandate_id=provider_mandate_id, status="CANCELLED")

    def get_mandate(self, provider_mandate_id: str) -> ProviderMandateResult:
        body = {"mid": self._settings.paytm_mid, "subscriptionId": provider_mandate_id}
        response = self._signed_request("/aoa-subscription/api/v2/subscription/status", body)
        status = response.get("body", {}).get("subscriptionStatus", "PENDING")
        return ProviderMandateResult(provider_mandate_id=provider_mandate_id, status=status)

    def execute_payment(
        self,
        idempotency_key: str,
        amount: float,
        merchant_id: str,
        mandate_provider_id: str | None = None,
    ) -> ProviderPaymentResult:
        # If tied to a mandate without autoRenewal, this maps to Paytm's
        # "Renew Subscription" API; a one-off NEW_PAYMENT charge with no
        # mandate maps to the standard PG "Initiate Transaction" API
        # instead. Both require a signed request the same shape as above —
        # left as a TODO pending real sandbox credentials to verify against.
        raise NotImplementedError(
            "PaytmSandboxProvider.execute_payment needs real sandbox credentials "
            "to build and verify against — see this file's module docstring. "
            "Use PAYMENT_PROVIDER=mock for a working demo in the meantime."
        )

    def get_payment_status(self, provider_transaction_id: str) -> ProviderPaymentResult:
        body = {"mid": self._settings.paytm_mid, "orderId": provider_transaction_id}
        response = self._signed_request("/order/status", body)
        status = response.get("body", {}).get("resultInfo", {}).get("resultStatus", "PENDING")
        return ProviderPaymentResult(
            provider_transaction_id=provider_transaction_id, status=status, amount=0.0
        )

    def refund_payment(self, provider_transaction_id: str, amount: float) -> ProviderPaymentResult:
        raise NotImplementedError("Refund flow not yet built — not required for the MVP demo scope.")