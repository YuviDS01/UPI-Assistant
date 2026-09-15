import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Append-only record of every meaningful state transition. NEVER write
    secrets or the UPI PIN here — metadata is for things like the policy
    decision, amounts, and merchant, not credentials.

    event_type examples: MANDATE_CREATED, MANDATE_PAUSED, MANDATE_RESUMED,
    POLICY_CHECKED, APPROVAL_CREATED, APPROVAL_APPROVED, APPROVAL_REJECTED,
    PAYMENT_EXECUTED, PAYMENT_SUCCEEDED, PAYMENT_FAILED, PAYMENT_SKIPPED_PAUSED.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "mandate" | "transaction" | ...
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "allowed" | "denied" | ...
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    log_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
