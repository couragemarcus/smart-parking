from sqlalchemy.ext.asyncio import AsyncSession
from app.models.parking import AuditLog

async def log_event(db: AsyncSession, actor: str, action: str, entity_type: str, entity_id: str = None, detail: str = None):
    log = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail
    )
    db.add(log)
    await db.commit()
