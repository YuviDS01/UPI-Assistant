"""
Payment tools. execute_payment is the safety-critical one — read
PaymentService.authorize_and_execute's docstring (Phase 6/7) before
touching this file. This tool passes NO authorization claim of its own;
the service derives authorization from DB state every time.
"""

import uuid

from langchain_core.tools import tool

from app.agent.tools._common import run_with_session, serialize_transaction
from app.core.exceptions import TransactionNotFoundError
from app.models import Mandate, Transaction
from app.models.enums import PaymentType
from app.payment_providers.factory import get_payment_provider
from app.services.payment_service import PaymentService
from app.services.transaction_service import TransactionService


@tool
def simulate_new_payment(
    user_id: str, merchant_id: str, merchant_name: str, category: str, amount: float
) -> dict:
    """
    Record a newly-detected one-off payment (prototype simulation of a
    payment feed — see docs). Creates a PENDING transaction; does not
    execute it. Use get_payment_details / check_payment_policy /
    execute_payment afterward to continue the NEW_PAYMENT workflow.
    """

    def _run(db):
        idempotency_key = f"new-{user_id}-{merchant_id}-{amount}-{uuid.uuid4().hex[:8]}"
        txn, _ = TransactionService.get_or_create(
            db,
            user_id=uuid.UUID(user_id),
            idempotency_key=idempotency_key,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            amount=amount,
            payment_type=PaymentType.NEW,
        )
        db.commit()
        return serialize_transaction(txn)

    return run_with_session(_run)


@tool
def get_payment_details(transaction_id: str) -> dict:
    """Fetch the stored details of a transaction (amount, merchant,
    category, current status). Never invent these fields yourself."""

    def _run(db):
        txn = db.get(Transaction, uuid.UUID(transaction_id))
        if txn is None:
            raise TransactionNotFoundError(f"No transaction found for id {transaction_id}.")
        return serialize_transaction(txn)

    return run_with_session(_run)


@tool
def execute_payment(transaction_id: str) -> dict:
    """
    Attempt to execute a payment. The backend independently determines
    whether this is authorized (via policy rules or an existing approved,
    unexpired approval request) — calling this tool does NOT itself
    authorize anything. If the result says requires_approval, call
    create_approval_request instead of retrying this.
    """

    def _run(db):
        txn = db.get(Transaction, uuid.UUID(transaction_id))
        if txn is None:
            raise TransactionNotFoundError(f"No transaction found for id {transaction_id}.")
        mandate = db.get(Mandate, txn.mandate_id) if txn.mandate_id else None
        provider = get_payment_provider()
        return PaymentService.authorize_and_execute(db, txn, provider, mandate=mandate)

    return run_with_session(_run)


@tool
def get_payment_status(transaction_id: str) -> dict:
    """Poll the current status of a transaction, refreshing from the
    payment provider if it was left PENDING."""

    def _run(db):
        txn = db.get(Transaction, uuid.UUID(transaction_id))
        if txn is None:
            raise TransactionNotFoundError(f"No transaction found for id {transaction_id}.")

        if txn.status == "PENDING" and txn.provider_transaction_id:
            provider = get_payment_provider()
            latest = provider.get_payment_status(txn.provider_transaction_id)
            if latest.status != txn.status:
                txn.status = latest.status
                txn.failure_reason = latest.failure_reason
                db.commit()
                db.refresh(txn)

        return serialize_transaction(txn)

    return run_with_session(_run)