import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health")
def health_check() -> dict:
    """Liveness check — process is up. Does not touch DB/Redis."""
    return {"status": "ok", "app_env": settings.app_env}


@router.get("/health/ready")
def readiness_check() -> dict:
    """Readiness check — confirms Postgres and Redis are actually reachable."""
    checks = {"database": "unknown", "redis": "unknown"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness probe, report and move on
        checks["database"] = f"error: {exc}"

    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    overall_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if overall_ok else "degraded", "checks": checks}
