import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MandateStatus


class Mandate(Base):
    """
    A standing authorization to pay a merchant on a recurring schedule.

    status:
      ACTIVE    - scheduler will execute on next_payment_date
      PAUSED    - scheduler SKIPS execution while paused_until is in the
                  future (or indefinitely if paused_until is NULL). The
                  underlying provider_mandate_id is untouched — this is the
                  "pause without cancelling" feature (docs/architecture.md §0).
      CANCELLED - terminal. Scheduler will never execute this mandate again.
      EXPIRED   - terminal. Set when a mandate's own end condition is reached.
    """

    __tablename__ = "mandates"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    amount_limit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "MONTHLY"
    next_payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    status: Mapped[MandateStatus] = mapped_column(
        String(20), nullable=False, default=MandateStatus.ACTIVE, index=True
    )

    # ── Pause/resume (USP) ──────────────────────────────────────────
    pause_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paused_until: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="NULL while paused means 'indefinite, until explicitly resumed'"
    )

    provider_mandate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="mandates")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="mandate")

    __table_args__ = (
        Index("ix_mandates_status_next_payment_date", "status", "next_payment_date"),
    )
