"""Service for managing rater sessions."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings


def get_rater_id_from_session(request: Request) -> UUID:
    """Get the rater ID from the session.

    If no rater ID exists in the session, create a new one.

    Args:
        request: The FastAPI request object.

    Returns:
        UUID: The rater's unique identifier.
    """
    session = request.session
    rater_id = session.get("rater_id")
    
    if not rater_id:
        rater_id = str(uuid4())
        session["rater_id"] = rater_id
    
    return UUID(rater_id)


def get_current_rater_id(request: Request) -> UUID:
    """Get the current rater's ID.

    This function gets the current rater's ID from the session.
    It will create a new rater ID if one doesn't exist.

    Args:
        request: The FastAPI request object.

    Returns:
        UUID: The current rater's ID.
    """
    return get_rater_id_from_session(request) 