import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta
from app.models.parking import ParkingSpace, SpaceState, VisitorSession, SessionState
from app.config import settings

# In-memory lock to serialize allocations for SQLite
allocation_lock = asyncio.Lock()

async def allocate_space(db: AsyncSession, session_id: int) -> ParkingSpace | None:
    async with allocation_lock:
        # Find lowest AVAILABLE space ordered by position ASC
        result = await db.execute(
            select(ParkingSpace)
            .where(ParkingSpace.state == SpaceState.AVAILABLE.value)
            .order_by(ParkingSpace.position.asc())
            .limit(1)
        )
        space = result.scalars().first()
        
        if not space:
            return None
            
        space.state = SpaceState.RESERVED.value
        space.reserved_at = datetime.now(timezone.utc)
        space.session_id = session_id
        
        await db.commit()
        await db.refresh(space)
        return space

async def release_space(db: AsyncSession, space_id: int) -> None:
    async with allocation_lock:
        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == space_id))
        space = result.scalars().first()
        if space:
            space.state = SpaceState.AVAILABLE.value
            space.session_id = None
            space.reserved_at = None
            space.occupied_at = None
            await db.commit()

async def confirm_space_occupied(db: AsyncSession, space_id: int) -> None:
    async with allocation_lock:
        result = await db.execute(select(ParkingSpace).where(ParkingSpace.id == space_id))
        space = result.scalars().first()
        if space:
            space.state = SpaceState.OCCUPIED.value
            space.occupied_at = datetime.now(timezone.utc)
            await db.commit()

async def check_and_expire_reservations(db: AsyncSession) -> list[int]:
    async with allocation_lock:
        timeout_delta = timedelta(minutes=settings.RESERVATION_TIMEOUT_MINUTES)
        now = datetime.now(timezone.utc)
        
        result = await db.execute(
            select(ParkingSpace).where(ParkingSpace.state == SpaceState.RESERVED.value)
        )
        spaces = result.scalars().all()
        
        released_spaces = []
        for space in spaces:
            if space.reserved_at and (now - space.reserved_at.replace(tzinfo=timezone.utc)) > timeout_delta:
                # Find associated session
                if space.session_id:
                    session_res = await db.execute(select(VisitorSession).where(VisitorSession.id == space.session_id))
                    session = session_res.scalars().first()
                    if session and session.state == SessionState.ASSIGNED.value:
                        session.state = SessionState.EXPIRED.value
                
                # Release space
                space.state = SpaceState.AVAILABLE.value
                space.session_id = None
                space.reserved_at = None
                space.occupied_at = None
                released_spaces.append(space.id)
                
        if released_spaces:
            await db.commit()
            
        return released_spaces

async def get_parking_layout(db: AsyncSession) -> dict:
    result = await db.execute(select(ParkingSpace).order_by(ParkingSpace.position.asc()))
    spaces = result.scalars().all()
    
    total = len(spaces)
    available = sum(1 for s in spaces if s.state == SpaceState.AVAILABLE.value)
    occupied = sum(1 for s in spaces if s.state == SpaceState.OCCUPIED.value)
    reserved = sum(1 for s in spaces if s.state == SpaceState.RESERVED.value)
    out_of_service = sum(1 for s in spaces if s.state == SpaceState.OUT_OF_SERVICE.value)
    
    return {
        "spaces": spaces,
        "total": total,
        "available": available,
        "occupied": occupied,
        "reserved": reserved,
        "out_of_service": out_of_service
    }
