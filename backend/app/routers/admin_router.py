import base64
import io
import qrcode
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.auth import get_current_admin
from app.models.parking import ParkingSpace, Configuration, AuditLog, VisitorSession, ArrivalEvent
from app.schemas.parking import SpaceOut, ConfigurationOut, ConfigurationUpdate, AuditLogOut, SessionOut, AdminSpaceMatch
from app.services.allocation import allocate_space
from app.services.session_service import assign_session_to_space, mark_session_departed
from app.services.websocket_hub import hub
from app.services.audit import log_event
from app.config import settings

router = APIRouter(dependencies=[Depends(get_current_admin)])

@router.get("/parking/spaces", response_model=list[SpaceOut])
async def get_admin_spaces(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace).order_by(ParkingSpace.position.asc()))
    return res.scalars().all()

@router.patch("/parking/spaces/{space_id}")
async def update_space(space_id: int, state: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ParkingSpace).where(ParkingSpace.id == space_id))
    space = res.scalars().first()
    if space:
        space.state = state
        await db.commit()
        await hub.broadcast_admin({"type": "space_updated", "space_id": space_id, "state": state})
    return {"status": "updated"}

@router.get("/configuration", response_model=ConfigurationOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Configuration))
    items = {c.key: c.value for c in res.scalars().all()}
    return ConfigurationOut(items=items)

@router.patch("/configuration")
async def update_config(config_in: ConfigurationUpdate, db: AsyncSession = Depends(get_db)):
    data = config_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        await db.execute(update(Configuration).where(Configuration.key == k).values(value=str(v)))
    await db.commit()
    await log_event(db, "admin", "config_update", "Configuration")
    return {"status": "updated"}

@router.get("/events", response_model=list[AuditLogOut])
async def get_events(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset))
    return res.scalars().all()

@router.get("/sessions", response_model=list[SessionOut])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(VisitorSession).order_by(VisitorSession.created_at.desc()))
    return res.scalars().all()

@router.post("/match")
async def admin_match(match_in: AdminSpaceMatch, db: AsyncSession = Depends(get_db)):
    res_sess = await db.execute(select(VisitorSession).where(VisitorSession.id == match_in.session_id))
    session = res_sess.scalars().first()
    if session:
        space = await allocate_space(db, session.id)
        if space:
            await assign_session_to_space(db, session, space)
            await log_event(db, "admin", "manual_match", "VisitorSession", str(session.id))
            await hub.send_to_visitor(session.token, {"type": "assigned", "space_name": space.name})
            await hub.broadcast_admin({"type": "allocation", "space_name": space.name, "session_id": session.id})
    return {"status": "matched"}

@router.post("/sessions/{session_id}/depart")
async def admin_depart(session_id: int, db: AsyncSession = Depends(get_db)):
    res_sess = await db.execute(select(VisitorSession).where(VisitorSession.id == session_id))
    session = res_sess.scalars().first()
    if session:
        await mark_session_departed(db, session)
        if session.space_id:
            res_space = await db.execute(select(ParkingSpace).where(ParkingSpace.id == session.space_id))
            space = res_space.scalars().first()
            if space:
                space.state = "AVAILABLE"
                space.session_id = None
                space.occupied_at = None
                space.reserved_at = None
        await db.commit()
        await log_event(db, "admin", "manual_depart", "VisitorSession", str(session.id))
    return {"status": "departed"}

@router.get("/qr")
async def get_qr_code():
    url = f"{settings.BACKEND_URL}/visitor"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {"qr_code_base64": img_str}
