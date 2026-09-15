def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_reports_db_and_redis(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert "database" in body["checks"]
    assert "redis" in body["checks"]
    # NOTE: if this ever fails with "error: ...", it means Postgres/Redis
    # aren't reachable from inside the backend container right now — that's
    # an environment problem, not a code bug. Check `docker compose ps`.
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
