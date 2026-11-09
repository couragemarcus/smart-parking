import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.parking import SimulatorArrivalIn, SimulatorDepartureIn, SpaceStatusIn
from app.models.parking import ArrivalEvent, VisitorSession, SessionState, ParkingSpace, SpaceState
from app.services.allocation import allocate_space, confirm_space_occupied, check_and_expire_reservations
from app.services.session_service import assign_session_to_space, mark_session_departed
from app.services.websocket_hub import hub

router = APIRouter()

@router.post("/arrival")
async def sim_arrival(arrival_in: SimulatorArrivalIn, db: AsyncSession = Depends(get_db)):
    idempotency_key = arrival_in.idempotency_key or str(uuid.uuid4())

    existing = await db.execute(
        select(ArrivalEvent).where(ArrivalEvent.idempotency_key == idempotency_key)
    )
    if existing.scalars().first():
        return {"status": "already_processed", "idempotency_key": idempotency_key}
    
    event = ArrivalEvent(
        idempotency_key=idempotency_key,
        sensor_type="simulator",
        raw_distance_cm=10.0,
        processed=True
    )
    db.add(event)
    
    oldest_session = await db.execute(
        select(VisitorSession)
        .where(VisitorSession.state == SessionState.ARRIVED.value)
        .order_by(VisitorSession.arrived_at.asc())
        .limit(1)
    )
    session = oldest_session.scalars().first()
    
    if session:
        space = await allocate_space(db, session.id)
        if space:
            await assign_session_to_space(db, session, space)
            event.matched_session_id = session.id
            await hub.send_to_visitor(session.token, {"type": "assigned", "space_name": space.name})
            await hub.broadcast_admin({"type": "allocation", "space_name": space.name, "session_id": session.id})
    await db.commit()
    return {"status": "simulated", "idempotency_key": idempotency_key}

@router.post("/departure")
async def sim_departure(dep_in: SimulatorDepartureIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace).where(ParkingSpace.name == dep_in.space_name))
    space = res.scalars().first()
    if space and space.state in [SpaceState.OCCUPIED.value, SpaceState.RESERVED.value]:
        session_id = space.session_id
        space.state = SpaceState.AVAILABLE.value
        space.session_id = None
        space.occupied_at = None
        space.reserved_at = None
        
        if session_id:
            res_sess = await db.execute(select(VisitorSession).where(VisitorSession.id == session_id))
            session = res_sess.scalars().first()
            if session:
                await mark_session_departed(db, session)
                
        await db.commit()
        await hub.broadcast_admin({"type": "space_vacated", "space_name": space.name})
    return {"status": "simulated"}

@router.post("/confirm-occupied")
async def sim_confirm_occupied(status_in: SpaceStatusIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace).where(ParkingSpace.name == status_in.space_name))
    space = res.scalars().first()
    if space and space.state == SpaceState.RESERVED.value:
        await confirm_space_occupied(db, space.id)
        if space.session_id:
            res_sess = await db.execute(select(VisitorSession).where(VisitorSession.id == space.session_id))
            session = res_sess.scalars().first()
            if session:
                session.state = SessionState.PARKED.value
                await db.commit()
        await hub.broadcast_admin({"type": "space_occupied", "space_name": space.name})
    return {"status": "simulated"}

@router.post("/reset")
async def sim_reset(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace))
    spaces = res.scalars().all()
    for space in spaces:
        space.state = SpaceState.AVAILABLE.value
        space.session_id = None
        space.occupied_at = None
        space.reserved_at = None
        
    res_sess = await db.execute(select(VisitorSession))
    for session in res_sess.scalars().all():
        session.state = SessionState.WAITING.value
        session.space_id = None
        
    await db.commit()
    await hub.broadcast_admin({"type": "reset"})
    return {"status": "reset"}

@router.post("/expire-reservations")
async def sim_expire(db: AsyncSession = Depends(get_db)):
    released = await check_and_expire_reservations(db)
    if released:
        await hub.broadcast_admin({"type": "reservations_expired", "spaces": released})
    return {"released_spaces": released}
