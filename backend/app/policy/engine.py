"""
The Policy Engine.

THIS IS THE SECURITY BOUNDARY. Read docs/architecture.md §11 and §36 before
touching this file.

Rules:
  - This module must NEVER import anything from app.agent.* — the LLM does
    not get to call into this code directly, only through a LangChain tool
    (Phase 7) that hands it a pre-formed PolicyResult it can only read.
  - Every method here is a pure function of its inputs (given the same DB
    state, the same call always returns the same result). No randomness,
    no "ask the model", no network calls.
  - "No rule found" always means "requires approval", never "auto-allow".
    Fail closed, not open.
"""

import uuid

from sqlalchemy.orm import Session

from app.models import Mandate, PaymentRule
from app.policy.models import PolicyResult


class PolicyEngine:
    def check_category_policy(
        self, db: Session, user_id: uuid.UUID, category: str, amount: float
    ) -> PolicyResult:
        """
        Used by the NEW_PAYMENT route (a detected payment with no mandate
        behind it). Looks up the user's per-category rule and decides
        deterministically.
        """
        rule = (
            db.query(PaymentRule)
            .filter(PaymentRule.user_id == user_id, PaymentRule.category == category)
            .first()
        )

        if rule is None:
            return PolicyResult(
                allowed=False,
                requires_approval=True,
                category=category,
                amount=amount,
                reason=f"No auto-approval rule exists for category '{category}'.",
            )

        max_amount = float(rule.max_amount)

        if not rule.auto_approve:
            return PolicyResult(
                allowed=False,
                requires_approval=True,
                category=category,
                amount=amount,
                limit_checked=max_amount,
                reason=f"Category '{category}' is configured to always require approval.",
            )

        if amount <= max_amount:
            return PolicyResult(
                allowed=True,
                requires_approval=False,
                category=category,
                amount=amount,
                limit_checked=max_amount,
                reason=f"Amount is within the auto-approval limit for '{category}'.",
            )

        return PolicyResult(
            allowed=False,
            requires_approval=True,
            category=category,
            amount=amount,
            limit_checked=max_amount,
            reason=f"Amount exceeds the auto-approval limit for '{category}'.",
        )

    def check_mandate_execution(self, mandate: Mandate, amount: float) -> PolicyResult:
        """
        Used by the RECURRING_PAYMENT route. A mandate's own amount_limit is
        the standing authorization — this does NOT check mandate.status
        (ACTIVE/PAUSED/CANCELLED/EXPIRED); that's MandateService's job
        (validate_mandate, run before this). This method answers exactly one
        question: is this specific amount within what was authorized?
        """
        limit = float(mandate.amount_limit)

        if amount <= limit:
            return PolicyResult(
                allowed=True,
                requires_approval=False,
                category=mandate.category,
                amount=amount,
                limit_checked=limit,
                reason="Amount is within the mandate's authorized limit.",
            )

        return PolicyResult(
            allowed=False,
            requires_approval=True,
            category=mandate.category,
            amount=amount,
            limit_checked=limit,
            reason="Amount exceeds the mandate's authorized limit.",
        )


def get_policy_engine() -> PolicyEngine:
    """FastAPI-dependency-friendly accessor. The engine is stateless, so a
    fresh instance per call is cheap and avoids any shared-state footguns."""
    return PolicyEngine()
