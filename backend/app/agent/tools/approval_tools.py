"""
Approval tools available to the agent. Deliberately limited to CREATING a
request and READING its status — approve_approval / reject_approval are
NOT exposed here. Only a human, through the real API endpoint
(POST /api/approvals/{id}/approve|reject), can grant or deny an approval.
The agent describing an approval and the agent GRANTING one must never be
the same action.
"""

import uuid

from langchain_core.tools import tool

from app.agent.tools._common import run_with_session, serialize_approval
from app.services.approval_service import ApprovalService


@tool
def create_approval_request(user_id: str, transaction_id: str, reason: str) -> dict:
    """
    Create a human approval request for a transaction that policy did not
    auto-approve. Does NOT execute the payment — it only creates the
    request; a human must approve it via the app before execute_payment
    will succeed.
    """

    def _run(db):
        approval = ApprovalService.create_approval_request(
            db, uuid.UUID(user_id), uuid.UUID(transaction_id), reason
        )
        return serialize_approval(approval)

    return run_with_session(_run)


@tool
def get_approval_status(approval_id: str) -> dict:
    """Check the current status of a previously created approval request."""

    def _run(db):
        approval = ApprovalService.get(db, uuid.UUID(approval_id))
        return serialize_approval(approval)

    return run_with_session(_run)