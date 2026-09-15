"""
Tests the router in isolation — no Claude call needed, since routing is a
pure function of an already-classified intent.
"""

from app.agent.router import route_from_intent


def test_pause_mandate_intent_routes_to_pause_node():
    assert route_from_intent({"intent": "PAUSE_MANDATE"}) == "pause_mandate"


def test_resume_mandate_intent_routes_to_resume_node():
    assert route_from_intent({"intent": "RESUME_MANDATE"}) == "resume_mandate"


def test_view_intents_all_route_to_query_node():
    for intent in ["VIEW_MANDATES", "VIEW_UPCOMING", "VIEW_HISTORY"]:
        assert route_from_intent({"intent": intent}) == "query"


def test_unrecognized_intent_routes_to_unknown():
    assert route_from_intent({"intent": "SOMETHING_MADE_UP"}) == "unknown"


def test_missing_intent_key_routes_to_unknown():
    assert route_from_intent({}) == "unknown"