"""
Pydantic (not SQLAlchemy) model for the policy engine's output.

This is the exact shape Claude sees when it calls the check_payment_policy
tool (Phase 7) — deliberately small and unambiguous. The agent reads
`allowed` / `requires_approval` and a human-readable `reason`; it never sees
raw rule rows or gets to negotiate the number.
"""

from pydantic import BaseModel


class PolicyResult(BaseModel):
    allowed: bool
    requires_approval: bool
    category: str
    amount: float
    limit_checked: float | None = None
    reason: str
