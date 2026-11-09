import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db, init_db, pwd_context
from app.main import app
from app.models.parking import ParkingSpace, Configuration, User, SpaceState
from app.config import settings

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        # Seed the four-space L1-L4 row
        for i in range(1, 5):
            session.add(ParkingSpace(name=f"L{i}", position=i, state=SpaceState.AVAILABLE.value))
        
        # Seed default config
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
            session.add(Configuration(key=k, value=v))
            
        session.add(User(username="admin", hashed_password=pwd_context.hash("admin123"), role="admin"))
        
        await session.commit()
        yield session

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
