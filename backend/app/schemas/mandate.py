import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Frequency = Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]


class MandateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: str
    merchant_name: str
    category: str
    amount_limit: float
    frequency: str
    next_payment_date: date
    status: str
    pause_reason: str | None
    paused_until: date | None
    provider_mandate_id: str | None
    created_at: datetime


class MandateCreate(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=255)
    merchant_name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    amount_limit: float = Field(gt=0, description="Must be a positive amount.")
    frequency: Frequency
    next_payment_date: date


class PauseMandateRequest(BaseModel):
    until: date | None = None
    reason: str | None = Field(default=None, max_length=255)