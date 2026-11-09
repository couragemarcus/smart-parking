import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from app.database import Base


class SpaceState(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class SessionState(str, enum.Enum):
    WAITING = "WAITING"
    ARRIVED = "ARRIVED"
    ASSIGNED = "ASSIGNED"
    PARKED = "PARKED"
    DEPARTED = "DEPARTED"
    EXPIRED = "EXPIRED"


class ParkingSpace(Base):
    """A physical parking bay. session_id is a soft reference (no FK) to avoid circular dependency."""

    __tablename__ = "parking_spaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    position = Column(Integer, nullable=False)
    state = Column(String, default=SpaceState.AVAILABLE.value, nullable=False)
    # Intentionally NOT a FK — avoids circular dependency with VisitorSession.
    session_id = Column(Integer, nullable=True)
    reserved_at = Column(DateTime(timezone=True), nullable=True)
    occupied_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class VisitorSession(Base):
    """An anonymous visitor's parking session."""

    __tablename__ = "visitor_sessions"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    state = Column(String, default=SessionState.WAITING.value, nullable=False)
    space_id = Column(Integer, ForeignKey("parking_spaces.id"), nullable=True)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ip_address = Column(String, nullable=True)


class ArrivalEvent(Base):
    """A sensor-detected vehicle arrival. Idempotency key prevents duplicate processing."""

    __tablename__ = "arrival_events"
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    sensor_type = Column(String, nullable=False)
    matched_session_id = Column(Integer, ForeignKey("visitor_sessions.id"), nullable=True)
    raw_distance_cm = Column(Float, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    processed = Column(Boolean, default=False, nullable=False)


class Configuration(Base):
    """Key-value store for runtime settings (institution name, thresholds, etc.)."""

    __tablename__ = "configuration"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class User(Base):
    """Admin or security staff user."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin" | "security"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AuditLog(Base):
    """Immutable record of significant system events."""

    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
