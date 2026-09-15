"""
Manual smoke test for the LangGraph agent. Not a pytest test — this makes
a REAL call to the Anthropic API, so it's meant to be run by hand once to
eyeball the behavior, not part of the automated suite (which would cost
money and be flaky on every CI run).

Run with:
    docker compose exec backend python -m app.scripts.smoke_test_graph
"""
import time
import uuid


from app.agent.graph import get_graph
from app.core.database import SessionLocal
from app.models import Mandate, User
from app.models.enums import MandateStatus


def _get_or_create_demo_mandate() -> tuple[str, str]:
    """Reuses the seeded demo user; creates a Netflix-like mandate to pause if one doesn't exist yet."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo.user@example.com").first()
        if user is None:
            raise SystemExit("Demo user not found. Run `python -m app.core.seed` first.")

        mandate = (
            db.query(Mandate)
            .filter(Mandate.user_id == user.id, Mandate.merchant_name == "Netflix")
            .first()
        )
        if mandate is None:
            from datetime import date

            mandate = Mandate(
                user_id=user.id,
                merchant_id="MERCH_NETFLIX",
                merchant_name="Netflix",
                category="subscriptions",
                amount_limit=649,
                frequency="MONTHLY",
                next_payment_date=date.today(),
                status=MandateStatus.ACTIVE,
                provider_mandate_id="MOCK_MANDATE_NETFLIX_DEMO",
            )
            db.add(mandate)
            db.commit()
            db.refresh(mandate)

        return str(user.id), str(mandate.id)
    finally:
        db.close()


def run(message: str, user_id: str, thread_id: str) -> None:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"user_id": user_id, "message": message}, config=config)

    print(f"\n--- USER: {message}")
    print(f"intent: {result.get('intent')}")
    print(f"mandate_id resolved: {result.get('mandate_id')}")
    print(f"ASSISTANT: {result.get('response')}")
    if result.get("tool_result"):
        print(f"tool_result: {result['tool_result']}")


if __name__ == "__main__":
    user_id, mandate_id = _get_or_create_demo_mandate()
    thread_id = str(uuid.uuid4())

    print(f"Demo user: {user_id}")
    print(f"Netflix mandate: {mandate_id}")

    run("pause my netflix payment for 2 months, I'm travelling", user_id, thread_id)
    time.sleep(15)
    run("show me my mandates", user_id, thread_id)
    time.sleep(15)
    run("actually resume my netflix payment", user_id, thread_id)