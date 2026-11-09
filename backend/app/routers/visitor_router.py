"""
Visitor-facing API endpoints.

All endpoints require a visitor token passed as:
  - Header: X-Visitor-Token: <token>
  - Query param: ?token=<token>  (convenient for WebSocket upgrades)

Visitor tokens are short-lived anonymous UUIDs created via POST /api/visitor/sessions.
They never carry personal identity.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.parking import VisitorSession, ParkingSpace
from app.schemas.parking import SessionOut, SpaceOut
from app.services.session_service import create_visitor_session, mark_session_arrived
from app.auth import get_visitor_session

router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionOut,
    summary="Create an anonymous visitor session (called after QR scan)",
)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Creates a new anonymous session and returns a unique visitor token.
    The frontend stores this token in localStorage and attaches it to every request.
    """
    ip = request.client.host if request.client else None
    session = await create_visitor_session(db, ip_address=ip)
    return session


@router.get("/me", response_model=SessionOut, summary="Get current session state")
async def get_my_session(session: VisitorSession = Depends(get_visitor_session)):
    """Return full session state for the authenticated visitor."""
    return session


@router.post(
    "/arrived",
    response_model=SessionOut,
    summary="Mark visitor as arrived at the entrance (joins the waiting queue)",
)
async def arrive(
    session: VisitorSession = Depends(get_visitor_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Transitions the session from WAITING → ARRIVED.
    The visitor is now in the queue to be matched with the next sensor event.
    Security or the simulator will trigger allocation.
    """
    updated_session = await mark_session_arrived(db, session)
    return updated_session


@router.get(
    "/assignment",
    summary="Get the visitor's current space assignment",
)
async def get_assignment(
    session: VisitorSession = Depends(get_visitor_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the visitor's session state and, if assigned, their space details.
    This is privacy-safe: only the token owner can see their own assignment.
    """
    space_out = None
    if session.space_id:
        res = await db.execute(select(ParkingSpace).where(ParkingSpace.id == session.space_id))
        space = res.scalars().first()
        if space:
            space_out = SpaceOut(
                id=space.id,
                name=space.name,
                position=space.position,
                state=space.state,
                session_id=None,  # do not leak session_id in response
                reserved_at=space.reserved_at,
                occupied_at=space.occupied_at,
            )

    return {
        "session": SessionOut.model_validate(session),
        "space": space_out,
    }
