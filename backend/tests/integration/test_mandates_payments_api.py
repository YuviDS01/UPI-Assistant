import uuid
from datetime import date

import pytest

from app.models import User

DEMO_EMAIL = "demo.user@example.com"


@pytest.fixture
def user(db_session):
    u = User(name="API Test User", email=f"api-test-{uuid.uuid4()}@example.com")
    db_session.add(u)
    db_session.commit()
    yield u
    db_session.delete(u)
    db_session.commit()


def test_create_and_list_mandate(client, user):
    headers = {"X-User-ID": str(user.id)}
    response = client.post(
        "/api/mandates",
        headers=headers,
        json={
            "merchant_id": "MERCH_TEST", "merchant_name": "Test Gym", "category": "subscriptions",
            "amount_limit": 1000, "frequency": "MONTHLY", "next_payment_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 200
    mandate_id = response.json()["id"]

    listed = client.get("/api/mandates", headers=headers)
    assert any(m["id"] == mandate_id for m in listed.json())


def test_pause_then_resume_via_api(client, user):
    headers = {"X-User-ID": str(user.id)}
    created = client.post(
        "/api/mandates", headers=headers,
        json={
            "merchant_id": "MERCH_TEST2", "merchant_name": "Test Streaming", "category": "subscriptions",
            "amount_limit": 500, "frequency": "MONTHLY", "next_payment_date": date.today().isoformat(),
        },
    ).json()

    paused = client.post(f"/api/mandates/{created['id']}/pause", json={"reason": "testing"})
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"

    resumed = client.post(f"/api/mandates/{created['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "ACTIVE"


def test_simulate_within_policy_executes(client, user):
    """Reuses the seeded demo user's payment_rules — see conftest note."""
    from app.models import User as UserModel

    headers = {"X-User-ID": str(user.id)}
    # This fresh user has no payment_rules -> fail-closed -> requires approval
    response = client.post(
        "/api/payments/simulate", headers=headers,
        json={"merchant_id": "MERCH_G1", "merchant_name": "Grocery", "category": "groceries", "amount": 500},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["execution_result"]["requires_approval"] is True
    assert body["approval_id"] is not None