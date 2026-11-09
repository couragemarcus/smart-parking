import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.parking import VisitorSession, SessionState, ParkingSpace
from app.config import settings

async def create_visitor_session(db: AsyncSession, ip_address: str = None) -> VisitorSession:
    token = str(uuid.uuid4())
    session = VisitorSession(
        token=token,
        state=SessionState.WAITING.value,
        ip_address=ip_address
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_session_by_token(db: AsyncSession, token: str) -> VisitorSession | None:
    result = await db.execute(select(VisitorSession).where(VisitorSession.token == token))
    return result.scalars().first()

async def mark_session_arrived(db: AsyncSession, session: VisitorSession) -> VisitorSession:
    session.state = SessionState.ARRIVED.value
    session.arrived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session

async def assign_session_to_space(db: AsyncSession, session: VisitorSession, space: ParkingSpace) -> VisitorSession:
    session.state = SessionState.ASSIGNED.value
    session.space_id = space.id
    session.assigned_at = datetime.now(timezone.utc)
    session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESERVATION_TIMEOUT_MINUTES)
    await db.commit()
    await db.refresh(session)
    return session

async def mark_session_parked(db: AsyncSession, session: VisitorSession) -> VisitorSession:
    session.state = SessionState.PARKED.value
    await db.commit()
    await db.refresh(session)
    return session

async def mark_session_departed(db: AsyncSession, session: VisitorSession) -> VisitorSession:
    session.state = SessionState.DEPARTED.value
    await db.commit()
    await db.refresh(session)
    return session
