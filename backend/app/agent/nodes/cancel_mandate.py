from app.agent.state import PaymentState
from app.agent.tools.mandate_tools import cancel_mandate as cancel_mandate_tool


def cancel_mandate_node(state: PaymentState) -> dict:
    mandate_id = state.get("mandate_id")
    if not mandate_id:
        return {"response": "I couldn't figure out which mandate you mean — could you name the merchant?"}

    result = cancel_mandate_tool.invoke({"mandate_id": mandate_id})
    if "error" in result:
        return {"error": result["message"], "response": f"I couldn't cancel that: {result['message']}"}

    return {
        "tool_result": result,
        "response": f"Cancelled your recurring payment to {result['merchant_name']}. This can't be undone — you'd need to set it up again if you change your mind.",
    }