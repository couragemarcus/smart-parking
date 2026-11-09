"""
Public parking information endpoints.

These endpoints are unauthenticated — anyone (including first-time visitors
who just scanned the QR code) can query destination info and the current
parking layout.

Privacy: the layout endpoint strips session_id from all spaces so no
visitor can infer information about another visitor's session.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.parking import DestinationInfo, ParkingLayout, SpaceOut
from app.services.allocation import get_parking_layout
from app.config import settings

router = APIRouter()


@router.get("/destination", response_model=DestinationInfo)
async def get_destination():
    """
    Return the parking lot location and Google Maps directions link.
    Called by the visitor welcome page immediately after QR scan.
    """
    return DestinationInfo(
        institution_name=settings.INSTITUTION_NAME,
        lat=settings.PARKING_LAT,
        lon=settings.PARKING_LON,
        google_maps_url=(
            f"https://www.google.com/maps/dir/?api=1"
            f"&destination={settings.PARKING_LAT},{settings.PARKING_LON}"
        ),
        waypoints=None,
    )


@router.get("/layout", response_model=ParkingLayout)
async def get_layout(db: AsyncSession = Depends(get_db)):
    """
    Return a privacy-safe parking layout.
    session_id is stripped from all spaces — visitors only know state colours.
    """
    layout = await get_parking_layout(db)
    # Mask session_id for visitor privacy
    safe_spaces = [
        SpaceOut(
            id=s.id,
            name=s.name,
            position=s.position,
            state=s.state,
            session_id=None,
            reserved_at=s.reserved_at,
            occupied_at=s.occupied_at,
        )
        for s in layout["spaces"]
    ]
    layout["spaces"] = safe_spaces
    return layout
