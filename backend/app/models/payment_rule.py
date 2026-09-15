import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentRule(Base):
    """
    Per-category auto-approve policy, e.g. "groceries <= 2000 -> auto-approve".
    Read by the deterministic Policy Engine (Phase 4) — never by the LLM directly.
    """

    __tablename__ = "payment_rules"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    max_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    auto_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="payment_rules")

    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_payment_rules_user_category"),)
