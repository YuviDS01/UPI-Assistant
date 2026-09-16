"""
Structural tests only — no real network call, since there are no live
Paytm sandbox credentials to test against. These verify the provider
enforces its own preconditions correctly, not that it actually talks to
Paytm successfully.
"""

import pytest

from app.core.config import get_settings
from app.payment_providers.factory import get_payment_provider


def test_factory_refuses_paytm_without_credentials(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PAYMENT_PROVIDER", "paytm")
    monkeypatch.setenv("PAYTM_MID", "")
    monkeypatch.setenv("PAYTM_MERCHANT_KEY", "")

    with pytest.raises(NotImplementedError):
        get_payment_provider()

    get_settings.cache_clear()


def test_factory_returns_mock_by_default(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    provider = get_payment_provider()
    assert type(provider).__name__ == "MockUPIProvider"
    get_settings.cache_clear()


def test_factory_rejects_unknown_provider_name(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PAYMENT_PROVIDER", "some_other_bank")
    with pytest.raises(ValueError):
        get_payment_provider()
    get_settings.cache_clear()