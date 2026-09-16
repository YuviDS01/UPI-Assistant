"""
Mandate CRUD routes. Every route now checks the mandate belongs to the
caller's X-User-ID — returns 404 (not 403) on mismatch, so a caller
probing another user's mandate IDs can't distinguish "doesn't exist" from
"exists but isn't yours" (standard IDOR-prevention practice).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.core.exceptions import MandateNotFoundError
from app.models import Mandate
from app.schemas.mandate import MandateCreate, MandateOut, PauseMandateRequest
from app.services.mandate_service import MandateService

router = APIRouter(prefix="/api/mandates", tags=["mandates"])


def _get_owned_mandate(db: Session, mandate_id: uuid.UUID, user_id: uuid.UUID) -> Mandate:
    mandate = MandateService.get_mandate(db, mandate_id)  # raises 404 if it doesn't exist at all
    if mandate.user_id != user_id:
        raise MandateNotFoundError(f"No mandate found for id {mandate_id}.")  # same 404, no leak
    return mandate


@router.get("", response_model=list[MandateOut])
def list_mandates(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> list[Mandate]:
    return db.query(Mandate).filter(Mandate.user_id == user_id).order_by(Mandate.created_at.desc()).all()


@router.post("", response_model=MandateOut)
def create_mandate(
    body: MandateCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Mandate:
    return MandateService.create_mandate(
        db,
        user_id=user_id,
        merchant_id=body.merchant_id,
        merchant_name=body.merchant_name,
        category=body.category,
        amount_limit=body.amount_limit,
        frequency=body.frequency,
        next_payment_date=body.next_payment_date,
    )


@router.get("/{mandate_id}", response_model=MandateOut)
def get_mandate(
    mandate_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Mandate:
    return _get_owned_mandate(db, mandate_id, user_id)


@router.post("/{mandate_id}/cancel", response_model=MandateOut)
def cancel_mandate(
    mandate_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Mandate:
    _get_owned_mandate(db, mandate_id, user_id)  # ownership check before mutating
    return MandateService.cancel_mandate(db, mandate_id)


@router.post("/{mandate_id}/pause", response_model=MandateOut)
def pause_mandate(
    mandate_id: uuid.UUID,
    body: PauseMandateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Mandate:
    _get_owned_mandate(db, mandate_id, user_id)
    return MandateService.pause_mandate(db, mandate_id, paused_until=body.until, reason=body.reason)


@router.post("/{mandate_id}/resume", response_model=MandateOut)
def resume_mandate(
    mandate_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Mandate:
    _get_owned_mandate(db, mandate_id, user_id)
    return MandateService.resume_mandate(db, mandate_id)