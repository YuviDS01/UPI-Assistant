"""
Loads the user's mandates and resolves any mandate_hint from classify_intent
("electricity", "netflix") to a real mandate_id by fuzzy-matching merchant
names. This is plain DB lookup — no LLM call.
"""

from app.agent.state import PaymentState
from app.agent.tools._common import serialize_mandate
from app.core.database import SessionLocal
from app.models import Mandate


def load_context(state: PaymentState) -> dict:
    db = SessionLocal()
    try:
        mandates = db.query(Mandate).filter(Mandate.user_id == state["user_id"]).all()
        serialized = [serialize_mandate(m) for m in mandates]

        resolved_mandate_id = None
        hint = (state.get("context") or {}).get("mandate_hint")
        if hint:
            hint_lower = hint.lower()
            for m in mandates:
                if hint_lower in m.merchant_name.lower() or hint_lower in m.category.lower():
                    resolved_mandate_id = str(m.id)
                    break

        return {
            "context": {"mandates": serialized},
            "mandate_id": resolved_mandate_id,
        }
    finally:
        db.close()