"""
Payment routes.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.core.exceptions import TransactionNotFoundError
from app.core.rate_limit import rate_limit
from app.models import Mandate, Transaction
from app.models.enums import MandateStatus, PaymentType
from app.payment_providers.factory import get_payment_provider
from app.schemas.mandate import MandateOut
from app.schemas.payment import SimulatePaymentRequest, TransactionOut
from app.services.approval_service import ApprovalService
from app.services.payment_service import PaymentService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[TransactionOut])
def list_payments(
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/upcoming", response_model=list[MandateOut])
def list_upcoming(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> list[Mandate]:
    return (
        db.query(Mandate)
        .filter(Mandate.user_id == user_id, Mandate.status == MandateStatus.ACTIVE)
        .order_by(Mandate.next_payment_date)
        .all()
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_payment(
    transaction_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.user_id != user_id:
        raise TransactionNotFoundError(f"No transaction found for id {transaction_id}.")
    return txn


@router.post("/simulate", dependencies=[Depends(rate_limit("simulate", max_requests=20, window_seconds=60))])
def simulate_payment(
    body: SimulatePaymentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    idempotency_key = f"sim-{user_id}-{body.merchant_id}-{body.amount}-{uuid.uuid4().hex[:8]}"
    txn, _ = TransactionService.get_or_create(
        db,
        user_id=user_id,
        idempotency_key=idempotency_key,
        merchant_id=body.merchant_id,
        merchant_name=body.merchant_name,
        category=body.category,
        amount=body.amount,
        payment_type=PaymentType.NEW,
    )
    db.commit()

    provider = get_payment_provider()
    result = PaymentService.authorize_and_execute(db, txn, provider)

    approval_id = None
    if result.get("requires_approval"):
        approval = ApprovalService.create_approval_request(
            db, user_id, txn.id, result.get("reason", "Outside automatic payment policy.")
        )
        db.commit()
        approval_id = str(approval.id)

    return {"transaction": TransactionOut.model_validate(txn), "execution_result": result, "approval_id": approval_id}