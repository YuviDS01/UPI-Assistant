"""
Centralized application configuration.

Why this exists:
Every other module (database, agent, payment providers) should read config
from here — never call os.environ directly elsewhere. That keeps all the
places a secret could leak in one auditable spot, and makes it trivial to
see the full list of env vars the app depends on.

Nothing here does I/O beyond reading environment variables — safe to import
from anywhere without side effects.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_name: str = "upi-payment-assistant"
    log_level: str = "INFO"

    # Database / cache — required from Phase 2 onward, unused in Phase 1
    database_url: str = ""
    redis_url: str = ""

    # AI — required from Phase 7 onward, unused in Phase 1
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"

    # Payment provider
    payment_provider: str = "mock"
    paytm_mid: str = ""
    paytm_merchant_key: str = ""
    paytm_env: str = "staging"

    # Dev auth
    dev_user_header: str = "X-User-ID"


@lru_cache
def get_settings() -> Settings:
    """
    Settings are cached (lru_cache) so the .env file / environment is only
    parsed once per process, not on every request.
    """
    return Settings()
