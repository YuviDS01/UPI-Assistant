"""
Shared dependencies for API routes.

get_db is re-exported from app.core.database so routes only ever import
from app.api.deps — one import surface, easy to swap later.

get_current_user_id is intentionally the ONLY place that knows how auth
works right now (an X-User-ID header, no real verification). When real auth
(Phase 14+) replaces this, every route stays the same — they just depend on
get_current_user_id and don't care how it's implemented.
"""

import uuid

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db  # noqa: F401  (re-exported)
from app.core.exceptions import UserNotFoundError, ValidationAppError
from app.models import User


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> uuid.UUID:
    """
    Prototype-only auth: trust the X-User-ID header. NEVER put a real secret
    or credential in this header — it is not a security boundary, it is a
    placeholder for real auth. See docs/security.md.
    """
    if not x_user_id:
        raise ValidationAppError(
            "Missing X-User-ID header.",
            detail={"hint": "Prototype auth requires an X-User-ID header with a valid user UUID."},
        )
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise ValidationAppError(
            "X-User-ID header is not a valid UUID.", detail={"received": x_user_id}
        ) from exc


def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """Resolves the header UUID to a real row — fails loudly if it doesn't exist."""
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"No user found for id {user_id}.", detail={"user_id": str(user_id)})
    return user
