"""
Read-only policy tools. These expose the PolicyEngine's decision to Claude
as data to relay to the user — Claude cannot influence the decision, only
read it. Actual money movement always re-runs this same check internally
(see PaymentService.authorize_and_execute) rather than trusting a prior
call to this tool.
"""

import uuid

from langchain_core.tools import tool

from app.agent.tools._common import run_with_session
from app.core.exceptions import MandateNotFoundError
from app.models import Mandate
from app.policy.engine import PolicyEngine


@tool
def check_payment_policy(user_id: str, category: str, amount: float) -> dict:
    """
    Check whether a payment of `amount` in `category` would be
    auto-approved for this user, based on their saved payment_rules. Use
    this to tell the user in advance whether something will need approval.
    This is informational only — it does not move money or create an
    approval request.
    """

    def _run(db):
        engine = PolicyEngine()
        result = engine.check_category_policy(db, uuid.UUID(user_id), category, amount)
        return result.model_dump()

    return run_with_session(_run)


@tool
def check_mandate_policy(mandate_id: str, amount: float) -> dict:
    """
    Check whether `amount` is within a specific mandate's authorized
    limit. Informational only.
    """

    def _run(db):
        mandate = db.get(Mandate, uuid.UUID(mandate_id))
        if mandate is None:
            raise MandateNotFoundError(f"No mandate found for id {mandate_id}.")
        engine = PolicyEngine()
        result = engine.check_mandate_execution(mandate, amount)
        return result.model_dump()

    return run_with_session(_run)