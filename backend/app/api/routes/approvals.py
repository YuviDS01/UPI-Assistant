"""
Approval API routes. Ownership is now enforced (approval.user_id must match
X-User-ID) and approve/reject are rate-limited since they trigger real
payment execution.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.core.exceptions import ApprovalNotFoundError
from app.core.rate_limit import rate_limit
from app.models import ApprovalRequest, Mandate
from app.models.enums import TransactionStatus
from app.payment_providers.factory import get_payment_provider
from app.schemas.approval import ApprovalOut
from app.services.approval_service import ApprovalService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _get_owned_approval(db: Session, approval_id: uuid.UUID, user_id: uuid.UUID) -> ApprovalRequest:
    approval = ApprovalService.get(db, approval_id)
    if approval.user_id != user_id:
        raise ApprovalNotFoundError(f"No approval request found for id {approval_id}.")
    return approval


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> list[ApprovalRequest]:
    return (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.user_id == user_id)
        .order_by(ApprovalRequest.created_at.desc())
        .all()
    )


@router.get("/{approval_id}", response_model=ApprovalOut)
def get_approval(
    approval_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ApprovalRequest:
    return _get_owned_approval(db, approval_id, user_id)


@router.post("/{approval_id}/approve", dependencies=[Depends(rate_limit("approve", max_requests=30, window_seconds=60))])
def approve_approval(
    approval_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    _get_owned_approval(db, approval_id, user_id)
    approval = ApprovalService.approve(db, approval_id)  # re-checks expiry itself
    transaction = approval.transaction
    mandate = db.get(Mandate, transaction.mandate_id) if transaction.mandate_id else None
    provider = get_payment_provider()

    result = PaymentService.authorize_and_execute(db, transaction, provider, mandate=mandate)

    return {"approval": ApprovalOut.model_validate(approval), "execution_result": result}


@router.post("/{approval_id}/reject", dependencies=[Depends(rate_limit("reject", max_requests=30, window_seconds=60))])
def reject_approval(
    approval_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    _get_owned_approval(db, approval_id, user_id)
    approval = ApprovalService.reject(db, approval_id)
    transaction = approval.transaction

    if transaction.status not in (
        TransactionStatus.SUCCESS,
        TransactionStatus.FAILED,
        TransactionStatus.CANCELLED,
    ):
        transaction.status = TransactionStatus.CANCELLED
        NotificationService.notify(
            db,
            transaction.user_id,
            title="Payment rejected",
            body=f"You rejected the ₹{transaction.amount} payment to {transaction.merchant_name}.",
        )
        db.commit()

    return {"approval": ApprovalOut.model_validate(approval)}