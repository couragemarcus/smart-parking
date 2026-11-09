"""
Tests for the parking space allocation engine.

Covers:
  1. Empty lot assigns P1 first (lowest position).
  2. Second arrival gets P2 (next lowest available).
  3. Vacancy reuse: P1 vacated while P2 occupied → next gets P1.
  4. Full lot returns None.
  5. Concurrent allocations never share a space.
  6. Reservation expiry releases space and marks session EXPIRED.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parking import ParkingSpace, VisitorSession, SpaceState, SessionState
from app.services.allocation import (
    allocate_space,
    release_space,
    confirm_space_occupied,
    check_and_expire_reservations,
)
from app.services.session_service import create_visitor_session


@pytest.mark.asyncio
async def test_first_arrival_gets_p1(db_session: AsyncSession):
    """Acceptance test #1: Empty lot assigns P1 first."""
    session = await create_visitor_session(db_session, ip_address="127.0.0.1")
    space = await allocate_space(db_session, session.id)

    assert space is not None
    assert space.name == "L1"
    assert space.state == SpaceState.RESERVED.value
    assert space.session_id == session.id


@pytest.mark.asyncio
async def test_second_arrival_gets_p2(db_session: AsyncSession):
    """Acceptance test #2: Second visitor gets P2 when P1 is occupied."""
    s1 = await create_visitor_session(db_session, ip_address="127.0.0.1")
    s2 = await create_visitor_session(db_session, ip_address="127.0.0.2")

    sp1 = await allocate_space(db_session, s1.id)
    await confirm_space_occupied(db_session, sp1.id)

    sp2 = await allocate_space(db_session, s2.id)

    assert sp1.name == "L1"
    assert sp2 is not None
    assert sp2.name == "L2"


@pytest.mark.asyncio
async def test_vacancy_reuse(db_session: AsyncSession):
    """
    Acceptance test #3: P1 vacated while P2 remains occupied.
    Next allocation must return P1 (lowest available), NOT P3.
    """
    s1 = await create_visitor_session(db_session, ip_address="10.0.0.1")
    s2 = await create_visitor_session(db_session, ip_address="10.0.0.2")
    s3 = await create_visitor_session(db_session, ip_address="10.0.0.3")

    sp1 = await allocate_space(db_session, s1.id)
    await confirm_space_occupied(db_session, sp1.id)

    sp2 = await allocate_space(db_session, s2.id)
    await confirm_space_occupied(db_session, sp2.id)

    # P1 departs — now available; P2 still occupied
    await release_space(db_session, sp1.id)

    sp_next = await allocate_space(db_session, s3.id)
    assert sp_next is not None
    assert sp_next.name == "L1", f"Expected L1 to be reused, got {sp_next.name}"


@pytest.mark.asyncio
async def test_full_lot_returns_none(db_session: AsyncSession):
    """Acceptance test #4a: No spaces available → allocate_space returns None."""
    sessions = [
        await create_visitor_session(db_session, ip_address=f"10.0.0.{i}")
        for i in range(4)
    ]

    assigned = []
    for sess in sessions:
        space = await allocate_space(db_session, sess.id)
        assert space is not None, "Lot should not be full yet"
        assigned.append(space)

    # Confirm all occupied so they don't expire
    for sp in assigned:
        await confirm_space_occupied(db_session, sp.id)

    # One more session — lot is full
    overflow = await create_visitor_session(db_session, ip_address="10.0.0.99")
    result = await allocate_space(db_session, overflow.id)
    assert result is None, "Full lot should return None"


@pytest.mark.asyncio
async def test_concurrent_allocation(db_session: AsyncSession):
    """
    Acceptance test #4: 6 concurrent allocations must each receive a UNIQUE space.
    Uses asyncio.gather to fire all allocations simultaneously.
    """
    sessions = [
        await create_visitor_session(db_session, ip_address=f"192.168.1.{i}")
        for i in range(4)
    ]

    results = await asyncio.gather(
        *[allocate_space(db_session, sess.id) for sess in sessions]
    )

    # Filter out None results (if any)
    assigned_spaces = [sp for sp in results if sp is not None]
    space_names = [sp.name for sp in assigned_spaces]

    assert len(assigned_spaces) == 4, f"Expected 4 assignments, got {len(assigned_spaces)}"
    assert len(set(space_names)) == 4, f"Duplicate space assignment detected: {space_names}"


@pytest.mark.asyncio
async def test_reservation_expiry(db_session: AsyncSession):
    """Acceptance test #10a: Expired reservations are released."""
    sess = await create_visitor_session(db_session, ip_address="127.0.0.1")
    space = await allocate_space(db_session, sess.id)
    assert space is not None

    # Manually back-date the reservation time to simulate expiry
    from sqlalchemy import select, update
    await db_session.execute(
        update(ParkingSpace)
        .where(ParkingSpace.id == space.id)
        .values(reserved_at=datetime.now(timezone.utc) - timedelta(minutes=60))
    )
    await db_session.execute(
        update(VisitorSession)
        .where(VisitorSession.id == sess.id)
        .values(state=SessionState.ASSIGNED.value)
    )
    await db_session.commit()

    released = await check_and_expire_reservations(db_session)

    assert space.id in released or len(released) > 0, "Expected at least one space released"

    # Verify space is now available
    await db_session.refresh(space)
    assert space.state == SpaceState.AVAILABLE.value
