"""
Approval API tests, per spec Tests 3 and 5 (§28): reject blocks execution,
an expired approval blocks execution even if the user "approves" it.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import ApprovalRequest, User
from app.models.enums import PaymentType, TransactionStatus
from app.services.approval_service import ApprovalService
from app.services.transaction_service import TransactionService


@pytest.fixture
def user(db_session):
    u = User(name="Approval Test User", email=f"approval-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def _make_out_of_policy_transaction(db_session, user):
    txn, _ = TransactionService.get_or_create(
        db_session, user_id=user.id, idempotency_key=f"approval-test-{uuid.uuid4()}",
        merchant_id="MERCH_1", merchant_name="XYZ Electronics", category="electronics",
        amount=15000, payment_type=PaymentType.NEW,
    )
    db_session.commit()
    return txn


def test_approve_out_of_policy_transaction_executes_it(client, db_session, user):
    txn = _make_out_of_policy_transaction(db_session, user)
    approval = ApprovalService.create_approval_request(db_session, user.id, txn.id, "Outside policy")
    db_session.commit()

    response = client.post(f"/api/approvals/{approval.id}/approve")
    assert response.status_code == 200
    body = response.json()
    assert body["approval"]["status"] == "APPROVED"
    assert body["execution_result"]["executed"] is True

    db_session.refresh(txn)
    assert txn.status == TransactionStatus.SUCCESS


def test_reject_blocks_execution(client, db_session, user):
    """Spec Test 3: user rejects -> payment not executed."""
    txn = _make_out_of_policy_transaction(db_session, user)
    approval = ApprovalService.create_approval_request(db_session, user.id, txn.id, "Outside policy")
    db_session.commit()

    response = client.post(f"/api/approvals/{approval.id}/reject")
    assert response.status_code == 200
    assert response.json()["approval"]["status"] == "REJECTED"

    db_session.refresh(txn)
    assert txn.status == TransactionStatus.CANCELLED


def test_approving_an_expired_approval_is_blocked(client, db_session, user):
    """Spec Test 5: expired approval attempts execution -> blocked."""
    txn = _make_out_of_policy_transaction(db_session, user)
    approval = ApprovalRequest(
        user_id=user.id,
        transaction_id=txn.id,
        reason="Outside policy",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # already expired
    )
    db_session.add(approval)
    db_session.commit()

    response = client.post(f"/api/approvals/{approval.id}/approve")
    assert response.status_code == 409
    assert response.json()["error_code"] == "APPROVAL_EXPIRED"

    db_session.refresh(txn)
    assert txn.status != TransactionStatus.SUCCESS


def test_get_unknown_approval_returns_404(client):
    response = client.get(f"/api/approvals/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error_code"] == "APPROVAL_NOT_FOUND"