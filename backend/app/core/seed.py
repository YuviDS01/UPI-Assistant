"""
Deterministic seed data so the dashboard has something to show as soon as
the app starts (spec §35). Safe to re-run: it checks for the demo user by
email first and skips seeding if already present, rather than duplicating
rows or crashing on the unique constraint.

Run with:
    docker compose exec backend python -m app.core.seed
"""

import uuid
from datetime import date, timedelta

from app.core.database import SessionLocal
from app.models import Mandate, PaymentRule, Transaction, User
from app.models.enums import MandateStatus, PaymentType, TransactionStatus

DEMO_EMAIL = "demo.user@example.com"


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"Demo user already exists ({existing.id}) — skipping seed.")
            return

        user = User(
            id=uuid.uuid4(),
            name="Demo User",
            email=DEMO_EMAIL,
            phone="+91-9999999999",
        )
        db.add(user)
        db.flush()  # get user.id without committing yet

        # Policy rules — spec §35
        db.add_all(
            [
                PaymentRule(user_id=user.id, category="groceries", max_amount=2000, auto_approve=True),
                PaymentRule(user_id=user.id, category="subscriptions", max_amount=1500, auto_approve=True),
            ]
        )

        # Active recurring mandate — electricity, monthly, ₹2,500 limit
        mandate = Mandate(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_id="MERCH_ELECTRICITY_001",
            merchant_name="State Electricity Board",
            category="utilities",
            amount_limit=2500,
            frequency="MONTHLY",
            next_payment_date=date.today() + timedelta(days=30),
            status=MandateStatus.ACTIVE,
        )
        db.add(mandate)
        db.flush()

        # Historical transactions — spec §35
        db.add_all(
            [
                Transaction(
                    user_id=user.id,
                    mandate_id=None,
                    merchant_id="MERCH_GROCERY_001",
                    merchant_name="Local Grocery Store",
                    category="groceries",
                    amount=1299,
                    payment_type=PaymentType.NEW,
                    status=TransactionStatus.SUCCESS,
                    provider_transaction_id="MOCK_TXN_SEED_001",
                    idempotency_key="seed-txn-001",
                ),
                Transaction(
                    user_id=user.id,
                    mandate_id=None,
                    merchant_id="MERCH_SUB_001",
                    merchant_name="Streaming Subscription Co",
                    category="subscriptions",
                    amount=899,
                    payment_type=PaymentType.NEW,
                    status=TransactionStatus.SUCCESS,
                    provider_transaction_id="MOCK_TXN_SEED_002",
                    idempotency_key="seed-txn-002",
                ),
                Transaction(
                    user_id=user.id,
                    mandate_id=None,
                    merchant_id="MERCH_ELECTRONICS_001",
                    merchant_name="XYZ Electronics",
                    category="electronics",
                    amount=8999,
                    payment_type=PaymentType.NEW,
                    status=TransactionStatus.PENDING,
                    idempotency_key="seed-txn-003",
                ),
            ]
        )

        db.commit()
        print(f"Seeded demo user {user.id} with 2 rules, 1 mandate, 3 transactions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
