"""
The ONE place that decides which PaymentProvider implementation is active,
based on the PAYMENT_PROVIDER env var. Everything else in the app calls
get_payment_provider() and gets back something typed as PaymentProvider —
it never imports MockUPIProvider or PaytmSandboxProvider directly.

This is what makes "swap the provider without touching the agent" true in
practice rather than just in the architecture doc: there is exactly one
import site to change (this function's body) when PaytmSandboxProvider
lands in Phase 13.
"""

from app.core.config import get_settings
from app.payment_providers.base import PaymentProvider
from app.payment_providers.mock_provider import get_mock_provider


def get_payment_provider() -> PaymentProvider:
    settings = get_settings()

    if settings.payment_provider == "mock":
        return get_mock_provider()

    if settings.payment_provider == "paytm":
        raise NotImplementedError(
            "PaytmSandboxProvider is not implemented yet (Phase 13). "
            "Set PAYMENT_PROVIDER=mock in .env to use the demo provider."
        )

    raise ValueError(f"Unknown PAYMENT_PROVIDER '{settings.payment_provider}'. Expected 'mock' or 'paytm'.")