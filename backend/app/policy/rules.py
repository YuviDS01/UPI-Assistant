"""
Constants for policy-adjacent decisions that aren't per-user rules and so
don't belong in the payment_rules table. Per-user amount/category rules
live entirely in the database (app.models.PaymentRule) — this file is NOT
where "the real limits" are; it exists only for system-wide defaults.
"""

# How long a human approval request stays valid before it must be treated
# as REJECTED regardless of what the user later clicks. Used by
# ApprovalService (Phase 9).
APPROVAL_EXPIRY_MINUTES = 30
