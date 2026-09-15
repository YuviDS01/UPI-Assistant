"""
Maps a classified intent to a graph node name. Intent classification does
NOT authorize anything — it only picks which deterministic workflow runs,
same as docs/architecture.md §5's routing diagram.
"""

from app.agent.state import PaymentState

ROUTE_MAP = {
    "CREATE_MANDATE": "create_mandate",
    "CANCEL_MANDATE": "cancel_mandate",
    "PAUSE_MANDATE": "pause_mandate",
    "RESUME_MANDATE": "resume_mandate",
    "VIEW_MANDATES": "query",
    "VIEW_UPCOMING": "query",
    "VIEW_HISTORY": "query",
    "NEW_PAYMENT": "new_payment",
    "RECURRING_PAYMENT": "recurring_payment",
    "UNKNOWN": "unknown",
}


def route_from_intent(state: PaymentState) -> str:
    return ROUTE_MAP.get(state.get("intent", "UNKNOWN"), "unknown")