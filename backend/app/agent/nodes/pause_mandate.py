"""
PAUSE_MANDATE route — the USP. See docs/architecture.md §0.
"""

from app.agent.state import PaymentState
from app.agent.tools.mandate_tools import pause_mandate as pause_mandate_tool


def pause_mandate_node(state: PaymentState) -> dict:
    mandate_id = state.get("mandate_id")
    if not mandate_id:
        return {"response": "Which recurring payment would you like to pause?"}

    result = pause_mandate_tool.invoke(
        {
            "mandate_id": mandate_id,
            "paused_until": state.get("pause_until"),
            "reason": state.get("reason"),
        }
    )
    if "error" in result:
        return {"error": result["message"], "response": f"I couldn't pause that: {result['message']}"}

    until_text = f"until {result['paused_until']}" if result["paused_until"] else "until you resume it"
    return {
        "tool_result": result,
        "response": (
            f"Paused payments to {result['merchant_name']} {until_text}. "
            f"Your mandate stays set up — no need to re-authorize anything when you're ready to resume."
        ),
    }