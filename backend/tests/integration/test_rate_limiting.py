import uuid

from app.models import User


def test_simulate_payment_is_rate_limited(client, db_session):
    user = User(name="Rate Limit Test User", email=f"rl-test-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    headers = {"X-User-ID": str(user.id)}

    responses = []
    for i in range(22):  # limit is 20/min
        r = client.post(
            "/api/payments/simulate",
            headers=headers,
            json={"merchant_id": f"MERCH_{i}", "merchant_name": "Test", "category": "groceries", "amount": 10},
        )
        responses.append(r.status_code)

    assert 429 in responses
    db_session.delete(user)
    db_session.commit()