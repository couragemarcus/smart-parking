from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.parking import SpaceState, SessionState

class SpaceOut(BaseModel):
    id: int
    name: str
    position: int
    state: SpaceState
    session_id: Optional[int] = None
    reserved_at: Optional[datetime] = None
    occupied_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class SessionOut(BaseModel):
    id: int
    token: str
    state: SessionState
    space_id: Optional[int] = None
    arrived_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SessionCreate(BaseModel):
    pass

class ArrivalEventIn(BaseModel):
    idempotency_key: str
    sensor_type: str
    raw_distance_cm: Optional[float] = None

class SpaceStatusIn(BaseModel):
    space_name: str
    occupied: bool

class SpaceUpdate(BaseModel):
    state: Optional[SpaceState] = None

class ConfigurationOut(BaseModel):
    items: dict[str, str]

class ConfigurationUpdate(BaseModel):
    institution_name: Optional[str] = None
    parking_lat: Optional[float] = None
    parking_lon: Optional[float] = None
    detection_threshold_cm: Optional[float] = None
    reservation_timeout_minutes: Optional[int] = None
    hardware_mode: Optional[bool] = None
    num_spaces: Optional[int] = None

class AuditLogOut(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ParkingLayout(BaseModel):
    spaces: List[SpaceOut]
    total: int
    available: int
    occupied: int
    reserved: int
    out_of_service: int

class DestinationInfo(BaseModel):
    institution_name: str
    lat: float
    lon: float
    google_maps_url: str
    waypoints: Optional[List[dict]] = None

class SimulatorArrivalIn(BaseModel):
    idempotency_key: Optional[str] = None

class SimulatorDepartureIn(BaseModel):
    space_name: str

class AdminSpaceMatch(BaseModel):
    session_id: int
    arrival_event_id: int
