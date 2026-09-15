"""
Human-in-the-loop approvals. expires_at is checked on every approve/reject
call — an approval past its expiry is treated as REJECTED no matter what
the user clicks (spec §16, §26): "do not assume that an earlier approval is
permanently valid."
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ApprovalExpiredError, ApprovalNotFoundError
from app.models import ApprovalRequest
from app.models.enums import ApprovalStatus
from app.policy.rules import APPROVAL_EXPIRY_MINUTES
from app.services.audit_service import AuditService


class ApprovalService:
    @staticmethod
    def create_approval_request(
        db: Session,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        reason: str,
        expiry_minutes: int = APPROVAL_EXPIRY_MINUTES,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            user_id=user_id,
            transaction_id=transaction_id,
            reason=reason,
            status=ApprovalStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        db.add(approval)
        db.flush()
        AuditService.log_event(
            db, "APPROVAL_CREATED", "approval_request", approval.id, user_id=user_id, reason=reason
        )
        return approval

    @staticmethod
    def get(db: Session, approval_id: uuid.UUID) -> ApprovalRequest:
        approval = db.get(ApprovalRequest, approval_id)
        if approval is None:
            raise ApprovalNotFoundError(f"No approval request found for id {approval_id}.")
        return approval

    @staticmethod
    def _expire_if_needed(db: Session, approval: ApprovalRequest) -> None:
        if approval.status == ApprovalStatus.PENDING and approval.expires_at < datetime.now(timezone.utc):
            approval.status = ApprovalStatus.EXPIRED
            db.flush()
            AuditService.log_event(
                db, "APPROVAL_EXPIRED", "approval_request", approval.id, user_id=approval.user_id
            )

    @staticmethod
    def approve(db: Session, approval_id: uuid.UUID) -> ApprovalRequest:
        approval = ApprovalService.get(db, approval_id)
        ApprovalService._expire_if_needed(db, approval)

        if approval.status == ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(
                f"Approval request {approval_id} expired at {approval.expires_at}.",
                detail={"approval_id": str(approval_id)},
            )
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalExpiredError(
                f"Approval request {approval_id} is already {approval.status} — cannot approve.",
            )

        approval.status = ApprovalStatus.APPROVED
        approval.approved_at = datetime.now(timezone.utc)
        db.flush()
        AuditService.log_event(
            db, "APPROVAL_APPROVED", "approval_request", approval.id, user_id=approval.user_id
        )
        return approval

    @staticmethod
    def reject(db: Session, approval_id: uuid.UUID) -> ApprovalRequest:
        approval = ApprovalService.get(db, approval_id)
        ApprovalService._expire_if_needed(db, approval)

        if approval.status == ApprovalStatus.PENDING:
            approval.status = ApprovalStatus.REJECTED
            approval.rejected_at = datetime.now(timezone.utc)
            db.flush()
            AuditService.log_event(
                db, "APPROVAL_REJECTED", "approval_request", approval.id, user_id=approval.user_id
            )
        return approval