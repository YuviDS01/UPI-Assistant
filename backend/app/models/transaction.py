import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TransactionStatus


class Transaction(Base):
    """
    One attempted (or completed) payment. mandate_id is NULL for one-off
    "new payment detected" flows that never had a mandate behind them.

    idempotency_key is the mechanism that makes execute_payment safe to call
    twice by accident — see PaymentService in Phase 6.
    """

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mandates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # RECURRING | NEW

    status: Mapped[TransactionStatus] = mapped_column(
        String(20), nullable=False, default=TransactionStatus.PENDING, index=True
    )

    provider_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="transactions")
    mandate: Mapped["Mandate | None"] = relationship(back_populates="transactions")
    approval_request: Mapped["ApprovalRequest | None"] = relationship(
        back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_transactions_user_status", "user_id", "status"),)
