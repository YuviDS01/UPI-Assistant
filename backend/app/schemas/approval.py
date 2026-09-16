import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    reason: str
    status: str
    expires_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime