import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApprovalStatus


class ApprovalRequest(Base):
    """
    Human-in-the-loop gate for a transaction that failed auto-approval.
    A transaction has zero or one approval request (enforced by the unique
    constraint on transaction_id).

    expires_at is checked by ApprovalService before honoring an approve/reject
    action — an expired request must be treated as REJECTED regardless of
    what the user clicks (see docs/architecture.md §3.4).
    """

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        String(20), nullable=False, default=ApprovalStatus.PENDING, index=True
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction: Mapped["Transaction"] = relationship(back_populates="approval_request")
