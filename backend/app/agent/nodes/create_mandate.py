"""
CREATE_MANDATE route. Prototype simplification: since a full multi-turn
slot-filling loop is out of scope, if required fields are missing this node
asks for them in one message rather than pausing/resuming state across
turns — the user just sends a follow-up message with the missing details.
"""

from app.agent.state import PaymentState
from app.agent.tools.mandate_tools import create_mandate as create_mandate_tool
from app.services.mandate_service import compute_next_payment_date

REQUIRED_FIELDS = ["merchant_name", "category", "amount", "frequency"]


def create_mandate_node(state: PaymentState) -> dict:
    missing = [f for f in REQUIRED_FIELDS if not state.get(f)]
    if missing:
        return {
            "response": (
                "I can set that up, but I still need: " + ", ".join(missing) +
                ". Could you tell me those?"
            )
        }

    next_date = state.get("next_payment_date") or compute_next_payment_date(
        state["frequency"]
    ).isoformat()

    result = create_mandate_tool.invoke(
        {
            "user_id": state["user_id"],
            "merchant_id": state["merchant_name"].upper().replace(" ", "_"),
            "merchant_name": state["merchant_name"],
            "category": state["category"],
            "amount_limit": state["amount"],
            "frequency": state["frequency"],
            "next_payment_date": next_date,
        }
    )

    if "error" in result:
        return {"error": result["message"], "response": f"I couldn't create that mandate: {result['message']}"}

    return {
        "tool_result": result,
        "response": (
            f"Done — I've set up a {result['frequency'].lower()} payment to "
            f"{result['merchant_name']}, up to ₹{result['amount_limit']:.0f}. "
            f"First payment: {result['next_payment_date']}."
        ),
    }