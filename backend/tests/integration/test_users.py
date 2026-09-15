from app.models import User

DEMO_EMAIL = "demo.user@example.com"


def test_me_without_header_returns_422_validation_error(client):
    response = client.get("/api/users/me")
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


def test_me_with_malformed_uuid_returns_422(client):
    response = client.get("/api/users/me", headers={"X-User-ID": "not-a-uuid"})
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_me_with_unknown_uuid_returns_404_user_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get("/api/users/me", headers={"X-User-ID": fake_id})
    assert response.status_code == 404
    assert response.json()["error_code"] == "USER_NOT_FOUND"


def test_me_with_seeded_demo_user_returns_profile(client, db_session):
    demo_user = db_session.query(User).filter(User.email == DEMO_EMAIL).first()
    assert demo_user is not None, (
        "Demo user not found — run `python -m app.core.seed` before running tests."
    )

    response = client.get("/api/users/me", headers={"X-User-ID": str(demo_user.id)})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == DEMO_EMAIL
    assert body["name"] == "Demo User"
