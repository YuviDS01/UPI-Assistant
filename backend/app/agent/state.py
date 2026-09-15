"""
The typed state that flows through every LangGraph node. Nothing sensitive
(no PIN, no credentials, no secrets) is ever stored here — see
docs/architecture.md §12 and §36.
"""

from typing import Literal, TypedDict

Intent = Literal[
    "CREATE_MANDATE",
    "CANCEL_MANDATE",
    "PAUSE_MANDATE",
    "RESUME_MANDATE",
    "VIEW_MANDATES",
    "VIEW_UPCOMING",
    "VIEW_HISTORY",
    "NEW_PAYMENT",
    "RECURRING_PAYMENT",
    "UNKNOWN",
]


class PaymentState(TypedDict, total=False):
    user_id: str
    message: str

    intent: Intent

    merchant_id: str | None
    merchant_name: str | None
    category: str | None
    amount: float | None
    frequency: str | None
    next_payment_date: str | None  # ISO date

    mandate_id: str | None
    pause_until: str | None  # ISO date, None = indefinite
    reason: str | None

    transaction_id: str | None
    approval_id: str | None

    context: dict | None  # loaded mandates/history for entity resolution

    tool_result: dict | None
    requires_approval: bool
    error: str | None

    response: str  # final natural-language reply shown to the user