from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import verify_device_credentials
from app.schemas.parking import ArrivalEventIn, SpaceStatusIn
from app.models.parking import ArrivalEvent, VisitorSession, SessionState, ParkingSpace, SpaceState
from app.services.allocation import allocate_space, confirm_space_occupied
from app.services.session_service import assign_session_to_space, mark_session_departed
from app.services.websocket_hub import hub
from app.services.audit import log_event

router = APIRouter(dependencies=[Depends(verify_device_credentials)])

@router.post("/arrival")
async def process_arrival(event_in: ArrivalEventIn, db: AsyncSession = Depends(get_db)):
    # Idempotency check
    existing = await db.execute(select(ArrivalEvent).where(ArrivalEvent.idempotency_key == event_in.idempotency_key))
    if existing.scalars().first():
        return {"status": "already_processed", "access": "BLOCKED"}
        
    event = ArrivalEvent(
        idempotency_key=event_in.idempotency_key,
        sensor_type=event_in.sensor_type,
        raw_distance_cm=event_in.raw_distance_cm,
        processed=True
    )
    db.add(event)
    
    # Find oldest waiting session
    oldest_session = await db.execute(
        select(VisitorSession)
        .where(VisitorSession.state == SessionState.ARRIVED.value)
        .order_by(VisitorSession.arrived_at.asc())
        .limit(1)
    )
    session = oldest_session.scalars().first()
    
    access = "BLOCKED"
    space_name = None
    if session:
        space = await allocate_space(db, session.id)
        if space:
            access = "GRANTED"
            space_name = space.name
            await assign_session_to_space(db, session, space)
            event.matched_session_id = session.id
            await hub.send_to_visitor(session.token, {"type": "assigned", "space_name": space.name})
            await hub.broadcast_admin({"type": "allocation", "space_name": space.name, "session_id": session.id})
            await log_event(db, "IOT", "arrival_assigned", "VisitorSession", str(session.id), f"Assigned to {space.name}")
        else:
            await log_event(db, "IOT", "arrival_unassigned", "ArrivalEvent", str(event.id), "Lot full")
    else:
        await log_event(db, "IOT", "arrival_no_session", "ArrivalEvent", str(event.id), "No arrived sessions")

    await db.commit()
    await hub.broadcast_admin(
        {
            "type": "access_decision",
            "access": access,
            "space_name": space_name,
            "arrival_event_id": event.id,
        }
    )
    return {
        "status": "processed",
        "access": access,
        "space_name": space_name,
        "session_matched": session is not None and access == "GRANTED",
    }

@router.post("/space-status")
async def update_space_status(status_in: SpaceStatusIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace).where(ParkingSpace.name == status_in.space_name))
    space = res.scalars().first()
    if not space:
        return {"status": "not_found"}
        
    if status_in.occupied and space.state == SpaceState.RESERVED.value:
        await confirm_space_occupied(db, space.id)
        if space.session_id:
            res_sess = await db.execute(select(VisitorSession).where(VisitorSession.id == space.session_id))
            session = res_sess.scalars().first()
            if session:
                session.state = SessionState.PARKED.value
                await db.commit()
        await hub.broadcast_admin({"type": "space_occupied", "space_name": space.name})
        
    elif not status_in.occupied and space.state == SpaceState.OCCUPIED.value:
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
        
    return {"status": "updated"}
