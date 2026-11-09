"""
API integration tests for the Smart Parking System.

Tests the full HTTP stack (FastAPI + SQLAlchemy) using an in-memory SQLite DB.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.parking import SessionState, SpaceState


@pytest.mark.asyncio
async def test_create_visitor_session(async_client: AsyncClient):
    """POST /api/visitor/sessions → returns token and id."""
    resp = await async_client.post("/api/visitor/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "id" in data
    assert len(data["token"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_get_my_session(async_client: AsyncClient):
    """GET /api/visitor/me → returns session state."""
    resp = await async_client.post("/api/visitor/sessions")
    token = resp.json()["token"]

    me = await async_client.get("/api/visitor/me", headers={"X-Visitor-Token": token})
    assert me.status_code == 200
    assert me.json()["state"] == "WAITING"


@pytest.mark.asyncio
async def test_visitor_arrived(async_client: AsyncClient):
    """POST /api/visitor/arrived → transitions to ARRIVED."""
    resp = await async_client.post("/api/visitor/sessions")
    token = resp.json()["token"]

    arrived = await async_client.post(
        "/api/visitor/arrived", headers={"X-Visitor-Token": token}
    )
    assert arrived.status_code == 200
    assert arrived.json()["state"] == "ARRIVED"


@pytest.mark.asyncio
async def test_simulator_arrival_assigns_space(async_client: AsyncClient):
    """
    Acceptance test workflow:
      1. Create session
      2. Mark arrived
      3. Simulate arrival → should get P1
    """
    # Create and arrive
    resp = await async_client.post("/api/visitor/sessions")
    token = resp.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": token})

    # Simulate sensor arrival
    sim = await async_client.post("/api/simulator/arrival", json={})
    assert sim.status_code == 200

    # Check assignment
    assignment = await async_client.get(
        "/api/visitor/assignment", headers={"X-Visitor-Token": token}
    )
    assert assignment.status_code == 200
    data = assignment.json()
    assert data["session"]["state"] in ("ASSIGNED", "PARKED")
    assert data["space"] is not None
    assert data["space"]["name"] == "L1"


@pytest.mark.asyncio
async def test_sensor_arrival_blocks_unmatched_access(async_client: AsyncClient):
    """A sensor event without a queued visitor must not open access."""
    response = await async_client.post(
        "/api/iot/arrival",
        json={
            "idempotency_key": "sensor-no-session-1",
            "sensor_type": "mock",
            "raw_distance_cm": 20,
        },
        headers={
            "X-Device-Id": "rpi-sensor-01",
            "X-Device-Secret": "change-device-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["access"] == "BLOCKED"
    assert response.json()["session_matched"] is False


@pytest.mark.asyncio
async def test_two_visitors_get_different_spaces(async_client: AsyncClient):
    """Acceptance test #4/#5: Two visitors get unique spaces."""
    # Visitor 1
    r1 = await async_client.post("/api/visitor/sessions")
    t1 = r1.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": t1})

    # Visitor 2
    r2 = await async_client.post("/api/visitor/sessions")
    t2 = r2.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": t2})

    # Trigger two arrivals
    await async_client.post("/api/simulator/arrival", json={})
    await async_client.post("/api/simulator/arrival", json={})

    a1 = (await async_client.get("/api/visitor/assignment", headers={"X-Visitor-Token": t1})).json()
    a2 = (await async_client.get("/api/visitor/assignment", headers={"X-Visitor-Token": t2})).json()

    sp1 = a1["space"]["name"] if a1["space"] else None
    sp2 = a2["space"]["name"] if a2["space"] else None

    assert sp1 is not None
    assert sp2 is not None
    assert sp1 != sp2, f"Both visitors got the same space: {sp1}"


@pytest.mark.asyncio
async def test_privacy_visitor_cannot_see_others(async_client: AsyncClient):
    """Acceptance test #5: Visitor can only see their own assignment, not others."""
    r1 = await async_client.post("/api/visitor/sessions")
    t1 = r1.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": t1})

    r2 = await async_client.post("/api/visitor/sessions")
    t2 = r2.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": t2})

    await async_client.post("/api/simulator/arrival", json={})
    await async_client.post("/api/simulator/arrival", json={})

    # Visitor 2 checking their assignment must NOT see visitor 1's session details
    a2 = await async_client.get("/api/visitor/assignment", headers={"X-Visitor-Token": t2})
    data = a2.json()

    # session_id must be null in space response (privacy-safe)
    if data["space"]:
        assert data["space"]["session_id"] is None

    # Visitor 2 cannot use visitor 1's token to get their assignment
    a_wrong = await async_client.get(
        "/api/visitor/assignment", headers={"X-Visitor-Token": "wrong-fake-token-xyz"}
    )
    assert a_wrong.status_code == 401


@pytest.mark.asyncio
async def test_admin_login(async_client: AsyncClient):
    """POST /api/auth/login/json → returns JWT."""
    resp = await async_client.post(
        "/api/auth/login/json",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_simulator_reset(async_client: AsyncClient, db_session):
    """POST /api/simulator/reset → all spaces become AVAILABLE."""
    # Create a session and assign it
    r1 = await async_client.post("/api/visitor/sessions")
    t1 = r1.json()["token"]
    await async_client.post("/api/visitor/arrived", headers={"X-Visitor-Token": t1})
    await async_client.post("/api/simulator/arrival", json={})

    # Reset
    reset = await async_client.post("/api/simulator/reset")
    assert reset.status_code == 200

    # Check layout
    layout = await async_client.get("/api/parking/layout")
    data = layout.json()
    assert data["available"] == 4
    assert data["reserved"] == 0
    assert data["occupied"] == 0


@pytest.mark.asyncio
async def test_parking_destination(async_client: AsyncClient):
    """GET /api/parking/destination → returns institution info."""
    resp = await async_client.get("/api/parking/destination")
    assert resp.status_code == 200
    data = resp.json()
    assert "institution_name" in data
    assert "lat" in data
    assert "lon" in data
    assert "google_maps_url" in data


@pytest.mark.asyncio
async def test_unauthenticated_admin_rejected(async_client: AsyncClient):
    """Admin endpoints must reject requests without a valid JWT."""
    resp = await async_client.get("/api/admin/parking/spaces")
    assert resp.status_code == 401
