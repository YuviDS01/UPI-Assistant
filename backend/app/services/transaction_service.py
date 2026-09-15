"""
TransactionService owns creation and status updates for `transactions` rows.
get_or_create_by_idempotency_key is the DB-level half of the idempotency
guarantee — MockUPIProvider already dedupes in-memory (Phase 5); this is the
second, durable layer, backed by the unique constraint on idempotency_key.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Transaction
from app.models.enums import TransactionStatus


class TransactionService:
    @staticmethod
    def get_by_idempotency_key(db: Session, idempotency_key: str) -> Transaction | None:
        return db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()

    @staticmethod
    def get_or_create(
        db: Session,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
        merchant_id: str,
        merchant_name: str,
        category: str,
        amount: float,
        payment_type: str,
        mandate_id: uuid.UUID | None = None,
        currency: str = "INR",
    ) -> tuple[Transaction, bool]:
        """Returns (transaction, created). If a transaction with this
        idempotency_key already exists, returns it unchanged — this is what
        makes calling the same payment request twice safe (spec Test 6)."""
        existing = TransactionService.get_by_idempotency_key(db, idempotency_key)
        if existing is not None:
            return existing, False

        txn = Transaction(
            user_id=user_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            amount=amount,
            currency=currency,
            payment_type=payment_type,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        db.add(txn)
        try:
            db.flush()
        except IntegrityError:
            # Race: someone else inserted the same idempotency_key between
            # our SELECT and our INSERT. Roll back and return their row.
            db.rollback()
            existing = TransactionService.get_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                return existing, False
            raise
        return txn, True