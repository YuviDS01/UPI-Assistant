"""
RECURRING_PAYMENT route — user-initiated ("pay my electricity bill now").
The scheduler (Phase 10) follows a separate, simpler path straight through
the services layer for its own automatic runs; this node exists for a user
explicitly asking to trigger a due mandate via chat.
"""

from app.agent.state import PaymentState
from app.agent.tools.payment_tools import execute_payment
from app.core.database import SessionLocal
from app.models import Mandate, Transaction
from app.models.enums import PaymentType
from app.services.transaction_service import TransactionService


def recurring_payment_node(state: PaymentState) -> dict:
    mandate_id = state.get("mandate_id")
    if not mandate_id:
        return {"response": "Which recurring payment would you like to run?"}

    db = SessionLocal()
    try:
        mandate = db.get(Mandate, mandate_id)
        if mandate is None:
            return {"response": "I couldn't find that mandate."}

        idempotency_key = f"recurring-{mandate.id}-{mandate.next_payment_date.isoformat()}"
        txn, _ = TransactionService.get_or_create(
            db,
            user_id=mandate.user_id,
            idempotency_key=idempotency_key,
            merchant_id=mandate.merchant_id,
            merchant_name=mandate.merchant_name,
            category=mandate.category,
            amount=float(mandate.amount_limit),
            payment_type=PaymentType.RECURRING,
            mandate_id=mandate.id,
        )
        db.commit()
        txn_id = str(txn.id)
    finally:
        db.close()

    result = execute_payment.invoke({"transaction_id": txn_id})

    if result.get("executed"):
        return {"transaction_id": txn_id, "tool_result": result, "response": f"Payment to {mandate.merchant_name} went through."}
    if result.get("status") == "SKIPPED":
        return {"tool_result": result, "response": f"That payment was skipped: {result.get('reason')}"}
    if result.get("requires_approval"):
        return {"tool_result": result, "response": f"That payment needs approval first: {result.get('reason')}"}
    return {"tool_result": result, "response": f"That payment didn't go through: {result.get('reason', 'unknown reason')}"}