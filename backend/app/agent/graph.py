"""
Builds and compiles the LangGraph. MemorySaver is used as the checkpointer
for now (Phase 8) — Phase 9 upgrades this to a Postgres-backed checkpointer
so an in-progress approval workflow survives a server restart, per
docs/architecture.md §16 ("do not rely on only in-memory state").
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.nodes.cancel_mandate import cancel_mandate_node
from app.agent.nodes.classify_intent import classify_intent
from app.agent.nodes.create_mandate import create_mandate_node
from app.agent.nodes.load_context import load_context
from app.agent.nodes.new_payment import new_payment_node
from app.agent.nodes.pause_mandate import pause_mandate_node
from app.agent.nodes.query import query_node
from app.agent.nodes.recurring_payment import recurring_payment_node
from app.agent.nodes.resume_mandate import resume_mandate_node
from app.agent.nodes.unknown import unknown_node
from app.agent.router import route_from_intent
from app.agent.state import PaymentState


def build_graph():
    graph = StateGraph(PaymentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("load_context", load_context)
    graph.add_node("create_mandate", create_mandate_node)
    graph.add_node("cancel_mandate", cancel_mandate_node)
    graph.add_node("pause_mandate", pause_mandate_node)
    graph.add_node("resume_mandate", resume_mandate_node)
    graph.add_node("new_payment", new_payment_node)
    graph.add_node("recurring_payment", recurring_payment_node)
    graph.add_node("query", query_node)
    graph.add_node("unknown", unknown_node)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "load_context")

    graph.add_conditional_edges(
        "load_context",
        route_from_intent,
        {
            "create_mandate": "create_mandate",
            "cancel_mandate": "cancel_mandate",
            "pause_mandate": "pause_mandate",
            "resume_mandate": "resume_mandate",
            "new_payment": "new_payment",
            "recurring_payment": "recurring_payment",
            "query": "query",
            "unknown": "unknown",
        },
    )

    for node_name in [
        "create_mandate", "cancel_mandate", "pause_mandate", "resume_mandate",
        "new_payment", "recurring_payment", "query", "unknown",
    ]:
        graph.add_edge(node_name, END)

    return graph.compile(checkpointer=MemorySaver())


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph