from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings
from passlib.context import CryptContext
import asyncio

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from app.models.parking import ParkingSpace, Configuration, User, VisitorSession, SpaceState
    from sqlalchemy import select
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Seed user
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            admin_user = User(
                username="admin", 
                hashed_password=pwd_context.hash("admin123"),
                role="admin"
            )
            session.add(admin_user)
            
        # Migrate the old P1-P6 prototype layout to the canonical L1-L4 row.
        existing_spaces = (await session.execute(select(ParkingSpace))).scalars().all()
        existing_by_name = {space.name: space for space in existing_spaces}
        for i in range(1, settings.NUM_SPACES + 1):
            old_space = existing_by_name.get(f"P{i}")
            new_name = f"L{i}"
            if old_space and new_name not in existing_by_name:
                old_space.name = new_name
                old_space.position = i
                existing_by_name[new_name] = old_space

        referenced_space_ids = {
            row[0]
            for row in (
                await session.execute(
                    select(VisitorSession.space_id).where(VisitorSession.space_id.is_not(None))
                )
            ).all()
        }
        for old_name in ("P5", "P6"):
            old_space = existing_by_name.get(old_name)
            if old_space and old_space.id not in referenced_space_ids and old_space.session_id is None:
                await session.delete(old_space)

        # Seed the four canonical spaces.
        for i in range(1, settings.NUM_SPACES + 1):
            name = f"L{i}"
            res = await session.execute(select(ParkingSpace).where(ParkingSpace.name == name))
            if not res.scalars().first():
                space = ParkingSpace(name=name, position=i, state=SpaceState.AVAILABLE.value)
                session.add(space)
                
        # Seed configuration
        defaults = {
            "institution_name": settings.INSTITUTION_NAME,
            "parking_lat": str(settings.PARKING_LAT),
            "parking_lon": str(settings.PARKING_LON),
            "detection_threshold_cm": str(settings.DETECTION_THRESHOLD_CM),
            "reservation_timeout_minutes": str(settings.RESERVATION_TIMEOUT_MINUTES),
            "hardware_mode": str(settings.HARDWARE_MODE).lower(),
            "num_spaces": str(settings.NUM_SPACES)
        }
        for k, v in defaults.items():
            res = await session.execute(select(Configuration).where(Configuration.key == k))
            if not res.scalars().first():
                conf = Configuration(key=k, value=v)
                session.add(conf)
                
        await session.commit()
