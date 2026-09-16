"""
The three end-to-end demos from the spec (§12), run as real integration
tests against the actual FastAPI app + Postgres — not mocks. If these pass,
the system genuinely does what the demo script claims.
"""

import uuid
from datetime import date

import pytest

from app.models import Mandate, Transaction, User
from app.models.enums import MandateStatus, TransactionStatus
from app.services.mandate_service import MandateService
from app.workers.payment_scheduler import process_due_mandates


@pytest.fixture
def user(db_session):
    u = User(name="Demo Test User", email=f"demo-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def test_demo_1_chat_created_mandate_executes_via_scheduler(client, db_session, user):
    """
    DEMO 1: chat -> intent classification -> create mandate -> confirmation
    -> scheduler -> policy check -> mock payment -> status -> notification.

    Note: this test creates the mandate directly via MandateService rather
    than through /api/chat, so it runs without a live Anthropic API call
    (classify_intent needs a real ANTHROPIC_API_KEY — see the smoke test
    script from Phase 8 for the actual chat-driven version of this demo).
    """
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_ELEC", "Electricity Board", "utilities",
        2500, "MONTHLY", date.today(),
    )
    assert mandate.status == MandateStatus.ACTIVE

    processed = process_due_mandates()
    assert processed >= 1

    txn = (
        db_session.query(Transaction)
        .filter(Transaction.mandate_id == mandate.id)
        .order_by(Transaction.created_at.desc())
        .first()
    )
    assert txn is not None
    assert txn.status == TransactionStatus.SUCCESS

    db_session.refresh(mandate)
    assert mandate.next_payment_date > date.today()  # scheduler advanced it


def test_demo_2_new_payment_outside_policy_requires_approval_then_executes(client, user):
    """
    DEMO 2: simulate a new payment -> policy check -> outside policy ->
    approval request -> frontend approval -> policy revalidation -> mock
    payment -> transaction status -> notification.
    """
    headers = {"X-User-ID": str(user.id)}

    simulate_response = client.post(
        "/api/payments/simulate",
        headers=headers,
        json={
            "merchant_id": "MERCH_XYZ", "merchant_name": "XYZ Electronics",
            "category": "electronics", "amount": 8999,
        },
    )
    assert simulate_response.status_code == 200
    body = simulate_response.json()
    assert body["execution_result"]["requires_approval"] is True
    approval_id = body["approval_id"]
    assert approval_id is not None

    approve_response = client.post(f"/api/approvals/{approval_id}/approve")
    assert approve_response.status_code == 200
    approve_body = approve_response.json()
    assert approve_body["execution_result"]["executed"] is True

    txn_id = body["transaction"]["id"]
    final = client.get(f"/api/payments/{txn_id}", headers=headers)
    assert final.json()["status"] == "SUCCESS"


def test_demo_3_pause_live_subscription_scheduler_skips_it_then_resume(db_session, user):
    """
    DEMO 3 (the USP): pause a due mandate -> scheduler skips it with zero
    money movement -> resume -> next due cycle executes normally.
    """
    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_NETFLIX", "Netflix", "subscriptions",
        649, "MONTHLY", date.today(), provider_mandate_id="MOCK_MANDATE_DEMO3",
    )

    MandateService.pause_mandate(db_session, mandate.id, paused_until=None, reason="not using it")
    process_due_mandates()

    db_session.refresh(mandate)
    assert mandate.status == MandateStatus.PAUSED
    assert mandate.provider_mandate_id == "MOCK_MANDATE_DEMO3"  # never touched
    txn_count_while_paused = (
        db_session.query(Transaction).filter(Transaction.mandate_id == mandate.id).count()
    )
    assert txn_count_while_paused == 0

    resumed = MandateService.resume_mandate(db_session, mandate.id)
    # Force it due again for the test (resume computed a future date, which
    # is correct real behavior — we're just fast-forwarding for the demo).
    resumed.next_payment_date = date.today()
    db_session.commit()

    process_due_mandates()

    txn = (
        db_session.query(Transaction).filter(Transaction.mandate_id == mandate.id).first()
    )
    assert txn is not None
    assert txn.status == TransactionStatus.SUCCESS


def test_cancel_view_upcoming_and_view_history_all_work(client, db_session, user):
    """Also demonstrate: cancel mandate, view upcoming payments, view payment history (spec §12)."""
    headers = {"X-User-ID": str(user.id)}

    mandate = MandateService.create_mandate(
        db_session, user.id, "MERCH_GYM", "City Gym", "subscriptions", 1500, "MONTHLY", date.today()
    )

    upcoming = client.get("/api/payments/upcoming", headers=headers)
    assert any(m["id"] == str(mandate.id) for m in upcoming.json())

    client.post("/api/mandates", headers=headers, json={  # a second mandate for good measure
        "merchant_id": "MERCH_MUSIC", "merchant_name": "Music Streaming", "category": "subscriptions",
        "amount_limit": 199, "frequency": "MONTHLY", "next_payment_date": date.today().isoformat(),
    })

    cancel_response = client.post(f"/api/mandates/{mandate.id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    upcoming_after = client.get("/api/payments/upcoming", headers=headers)
    assert not any(m["id"] == str(mandate.id) for m in upcoming_after.json())  # cancelled mandate drops off

    history = client.get("/api/payments", headers=headers)
    assert history.status_code == 200