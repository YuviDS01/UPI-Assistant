from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the profile of whoever the X-User-ID header points at.
    Exists mostly to prove the dependency chain (header -> UUID -> DB row
    -> 404 if missing) works before we build real business routes on top
    of it in Phase 6+.
    """
    return current_user
