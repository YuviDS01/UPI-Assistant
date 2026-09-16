import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mandate_id: uuid.UUID | None
    merchant_id: str
    merchant_name: str
    category: str
    amount: float
    currency: str
    payment_type: str
    status: str
    provider_transaction_id: str | None
    failure_reason: str | None
    created_at: datetime


class SimulatePaymentRequest(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=255)
    merchant_name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, description="Must be a positive amount.")