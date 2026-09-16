"""
Postgres-backed checkpointer for LangGraph (Phase 9). An approval-pending
(or any in-progress) conversation survives a server restart, per
docs/architecture.md §16: "do not rely on only in-memory state."

IMPORTANT — the bug this file fixes:
PostgresSaver.from_conn_string() returns a context manager, not a saver
directly. You must keep a reference to THAT context manager object
(_checkpointer_cm below), not just the result of calling __enter__() on
it — otherwise the context manager has no references left once this
function returns, so Python's garbage collector is free to clean it up at
any later point. When it does, the underlying database connection gets
closed out from under the saver you're still actively using, producing a
delayed, unpredictable `psycopg.OperationalError: the connection is
closed` the next time a request tries to use it — not an immediate,
easy-to-diagnose failure.

Note @lru_cache is deliberately NOT used here: lru_cache only protects the
function's *return value* from being recomputed — it does nothing to keep
the context manager object itself alive, so it would give false
confidence while not actually fixing the bug above. A plain module-level
global is what actually holds the reference.
"""

from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings


def _to_psycopg_dsn(sqlalchemy_url: str) -> str:
    """SQLAlchemy's URL has a +psycopg driver suffix; the raw psycopg
    client library doesn't understand that suffix and wants a plain
    postgresql:// DSN."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


# Module-level globals — intentionally hold BOTH the context manager and
# the saver it produced, for the whole life of the process.
_checkpointer_cm = None
_checkpointer: PostgresSaver | None = None


def get_checkpointer() -> PostgresSaver:
    global _checkpointer_cm, _checkpointer

    if _checkpointer is None:
        settings = get_settings()
        dsn = _to_psycopg_dsn(settings.database_url)

        _checkpointer_cm = PostgresSaver.from_conn_string(dsn)
        _checkpointer = _checkpointer_cm.__enter__()
        # setup() creates the checkpoint tables if they don't exist yet —
        # idempotent, safe to call on every process startup.
        _checkpointer.setup()

    return _checkpointer