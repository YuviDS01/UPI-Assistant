"""
NEW_PAYMENT route: record the detected payment, check policy, execute if
allowed, otherwise create an approval request and stop — a human must act
through the approval UI before anything executes further.
"""

from app.agent.state import PaymentState
from app.agent.tools.approval_tools import create_approval_request
from app.agent.tools.payment_tools import execute_payment, simulate_new_payment

REQUIRED_FIELDS = ["merchant_name", "category", "amount"]


def new_payment_node(state: PaymentState) -> dict:
    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]
    if missing:
        return {"response": "I need a bit more detail: " + ", ".join(missing) + "."}

    created = simulate_new_payment.invoke(
        {
            "user_id": state["user_id"],
            "merchant_id": state["merchant_name"].upper().replace(" ", "_"),
            "merchant_name": state["merchant_name"],
            "category": state["category"],
            "amount": state["amount"],
        }
    )
    if "error" in created:
        return {"error": created["message"], "response": f"Couldn't record that payment: {created['message']}"}

    txn_id = created["transaction_id"]
    result = execute_payment.invoke({"transaction_id": txn_id})

    if result.get("executed"):
        return {
            "transaction_id": txn_id,
            "tool_result": result,
            "response": f"₹{state['amount']:.0f} to {state['merchant_name']} went through automatically — it was within your policy for {state['category']}.",
        }

    if result.get("requires_approval"):
        approval = create_approval_request.invoke(
            {
                "user_id": state["user_id"],
                "transaction_id": txn_id,
                "reason": result.get("reason", "Outside automatic payment policy."),
            }
        )
        return {
            "transaction_id": txn_id,
            "approval_id": approval.get("approval_id"),
            "requires_approval": True,
            "tool_result": result,
            "response": (
                f"₹{state['amount']:.0f} to {state['merchant_name']} is outside your automatic policy "
                f"for {state['category']}, so I've created an approval request — you'll need to approve "
                f"or reject it before it goes through."
            ),
        }

    return {"tool_result": result, "response": f"That payment could not be processed: {result.get('reason', 'unknown reason')}."}