"""
FastAPI application entry point for the Smart Parking Management System.

Startup:
  - Creates all DB tables and seeds initial data (spaces, config, admin user)
  - Starts a background task that checks for expired reservations every 30 s

Routes:
  /api/auth        - JWT login / auth
  /api/visitor     - Visitor session management
  /api/parking     - Public parking info (destination, layout)
  /api/iot         - Device-authenticated sensor events
  /api/admin       - Admin-only management
  /api/simulator   - Simulation endpoints (all modes)
  /ws/visitor      - Per-visitor WebSocket (session-specific)
  /ws/admin        - Admin broadcast WebSocket
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.routers import auth_router, visitor_router, iot_router, admin_router, simulator_router
from app.routers.parking_router import router as parking_router
from app.services.websocket_hub import hub
from app.services.allocation import check_and_expire_reservations
from app.auth import verify_token


# ---------------------------------------------------------------------------
# Background expiry task
# ---------------------------------------------------------------------------

async def _expiry_task() -> None:
    """Periodically expire stale reservations and notify connected admins."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                released = await check_and_expire_reservations(db)
                if released:
                    await hub.broadcast_admin(
                        {"type": "reservations_expired", "released_space_ids": released}
                    )
        except Exception as exc:  # pragma: no cover
            # Do not crash the task on transient errors
            print(f"[expiry_task] error: {exc}")
        await asyncio.sleep(30)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(_expiry_task())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Parking API",
    description="IoT-based parking management system — visitor, admin, and device endpoints.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(visitor_router.router, prefix="/api/visitor", tags=["visitor"])
app.include_router(parking_router, prefix="/api/parking", tags=["parking"])
app.include_router(iot_router.router, prefix="/api/iot", tags=["iot"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["admin"])
app.include_router(simulator_router.router, prefix="/api/simulator", tags=["simulator"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# WebSocket: visitor (session-specific, private)
# ---------------------------------------------------------------------------

@app.websocket("/ws/visitor")
async def websocket_visitor(websocket: WebSocket, token: str = Query(...)):
    """
    Session-specific WebSocket for visitors.
    Each visitor token maps to an isolated channel — no cross-contamination.
    """
    await hub.connect_visitor(token, websocket)
    try:
        while True:
            # Keep alive — we only push from server side
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        hub.disconnect_visitor(token)


# ---------------------------------------------------------------------------
# WebSocket: admin broadcast channel
# ---------------------------------------------------------------------------

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket, token: str = Query(...)):
    """
    Admin broadcast WebSocket. Requires a valid JWT with role=admin.
    """
    payload = verify_token(token)
    if not payload or payload.get("role") not in ("admin", "security"):
        await websocket.close(code=4001)
        return

    await hub.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        hub.disconnect_admin(websocket)
