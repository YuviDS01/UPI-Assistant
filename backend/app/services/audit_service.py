"""
Append-only audit trail. Deliberately the simplest service in the codebase
— it does one thing: write a row. Every other service calls into this one
whenever it makes a decision worth remembering.

IMPORTANT: this does NOT commit the DB session. The audit row is meant to
land in the SAME database transaction as the state change it documents
(e.g. mandate.status = PAUSED and the MANDATE_PAUSED audit row commit or
roll back together) — see docs/architecture.md §27.
"""

import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        decision: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            decision=decision,
            reason=reason,
            log_metadata=metadata,
        )
        db.add(entry)
        db.flush()
        return entry