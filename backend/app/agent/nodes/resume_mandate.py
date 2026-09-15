from app.agent.state import PaymentState
from app.agent.tools.mandate_tools import resume_mandate as resume_mandate_tool


def resume_mandate_node(state: PaymentState) -> dict:
    mandate_id = state.get("mandate_id")
    if not mandate_id:
        return {"response": "Which paused payment would you like to resume?"}

    result = resume_mandate_tool.invoke({"mandate_id": mandate_id})
    if "error" in result:
        return {"error": result["message"], "response": f"I couldn't resume that: {result['message']}"}

    return {
        "tool_result": result,
        "response": f"Resumed payments to {result['merchant_name']}. Next payment: {result['next_payment_date']}.",
    }