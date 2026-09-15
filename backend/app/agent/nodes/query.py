"""
QUERY route (VIEW_MANDATES / VIEW_UPCOMING / VIEW_HISTORY). Formats
already-fetched tool data into plain text — never fabricates a row.
"""

from app.agent.state import PaymentState
from app.agent.tools.query_tools import get_payment_history, get_upcoming_payments


def query_node(state: PaymentState) -> dict:
    intent = state["intent"]
    mandates = (state.get("context") or {}).get("mandates", [])

    if intent == "VIEW_MANDATES":
        if not mandates:
            return {"response": "You don't have any mandates set up yet."}
        lines = [f"- {m['merchant_name']}: ₹{m['amount_limit']:.0f} {m['frequency'].lower()} ({m['status']})" for m in mandates]
        return {"tool_result": {"mandates": mandates}, "response": "Your mandates:\n" + "\n".join(lines)}

    if intent == "VIEW_UPCOMING":
        upcoming = get_upcoming_payments.invoke({"user_id": state["user_id"]})
        if not upcoming:
            return {"response": "No upcoming payments in the next 30 days."}
        lines = [f"- {m['merchant_name']}: ₹{m['amount_limit']:.0f} on {m['next_payment_date']}" for m in upcoming]
        return {"tool_result": {"upcoming": upcoming}, "response": "Upcoming payments:\n" + "\n".join(lines)}

    if intent == "VIEW_HISTORY":
        history = get_payment_history.invoke({"user_id": state["user_id"], "limit": 10})
        if not history:
            return {"response": "No payment history yet."}
        lines = [f"- {t['merchant_name']}: ₹{t['amount']:.0f} ({t['status']})" for t in history]
        return {"tool_result": {"history": history}, "response": "Recent payments:\n" + "\n".join(lines)}

    return {"response": "I'm not sure what you'd like to see."}