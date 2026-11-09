# Smart Parking Management System

A complete IoT-based parking management system for institutions (universities, hotels, offices). Built with Raspberry Pi, FastAPI, React, and real-time WebSockets.

---

## Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)

### 1. Clone and configure
```bash
cd smart-parking
cp .env.example .env
# Edit .env with your institution name, coordinates, and secrets
```

### 2. Run the backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
First run automatically creates `parking.db`, seeds 6 spaces (P1–P6), default config, and admin user.

### 3. Run the frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

### 4. Default credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |

> **Change these immediately in production.**

---

## Docker Compose (Recommended)
```bash
cp .env.example .env
docker compose up --build
```
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Demo Walkthrough

### Visitor Flow
1. Open http://localhost:5173 on your phone (or scan the QR code from the admin dashboard)
2. See the welcome page with the institution name, map, and directions button
3. Tap **Start Parking Session**
4. You'll see the dashboard in "Waiting" state
5. Tap **I Have Arrived** to join the queue
6. Go to http://localhost:5173/simulator → click **Simulate Arrival**
7. Your phone shows the assigned space (e.g. P2) with a **blinking green border**
8. In the simulator, click **Confirm Occupied** → status updates to "Parking confirmed"

### Multi-Visitor Test
1. Open http://localhost:5173 in a second browser/tab (incognito)
2. Create a second session and mark arrived
3. Simulate another arrival → second visitor gets the next space
4. Each visitor sees only their own assignment

### Admin Flow
1. Go to http://localhost:5173/admin
2. Login with admin / admin123
3. See the live parking layout, QR code, configuration, and audit logs
4. Use the **Match & Assign** button to manually link an arrival event to a session
5. Edit institution name, coordinates, detection threshold

---

## Architecture

```
Visitor Phone  ──HTTPS──►  FastAPI Backend  ◄──HTTPS──  Raspberry Pi Sensor
     │                          │                              │
     │ WSS /ws/visitor          │ SQLite / PostgreSQL          │ POST /api/iot/arrival
     ▼                          │                              │
Dashboard (React PWA)    Allocation Engine              HC-SR04 Sensor
                        (atomic left-to-right)
```

### Allocation Rules
- Always assign lowest-numbered **AVAILABLE** space (P1 before P2, etc.)
- P1 vacated while P2 occupied → next arrival gets P1 (not P3)
- Atomic under concurrency — two simultaneous arrivals never share a space
- States: `AVAILABLE → RESERVED → OCCUPIED → AVAILABLE`

### Space States
| State | Colour | Description |
|-------|--------|-------------|
| AVAILABLE | 🟢 Green | Ready to assign |
| RESERVED | 🟡 Yellow | Assigned, driver en route |
| OCCUPIED | 🔴 Red | Vehicle parked |
| OUT_OF_SERVICE | ⚫ Gray | Disabled by admin |

---

## API Reference

Full interactive docs at http://localhost:8000/docs (Swagger UI)

### Key Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/visitor/sessions` | None | Create anonymous visitor session |
| `GET` | `/api/visitor/me` | Visitor token | Get session state |
| `POST` | `/api/visitor/arrived` | Visitor token | Mark arrived at entrance |
| `GET` | `/api/visitor/assignment` | Visitor token | Get space assignment |
| `GET` | `/api/parking/destination` | None | Parking location + directions |
| `GET` | `/api/parking/layout` | None | Current space states |
| `WS` | `/ws/visitor?token=TOKEN` | Visitor token | Real-time session updates |
| `POST` | `/api/iot/arrival` | Device creds | Sensor arrival event |
| `POST` | `/api/iot/space-status` | Device creds | Space occupancy update |
| `POST` | `/api/auth/login` | None | Admin/security login |
| `GET` | `/api/admin/parking/spaces` | Admin JWT | All spaces with detail |
| `PATCH` | `/api/admin/configuration` | Admin JWT | Update settings |
| `GET` | `/api/admin/events` | Admin JWT | Audit log |
| `GET` | `/api/admin/qr` | Admin JWT | QR code for site |
| `POST` | `/api/simulator/arrival` | None | Simulate vehicle detection |
| `POST` | `/api/simulator/departure` | None | Simulate vehicle leaving |
| `POST` | `/api/simulator/reset` | None | Reset all spaces |
| `WS` | `/ws/admin?token=JWT` | Admin JWT | Real-time admin events |

---

## Raspberry Pi Hardware Setup

See [`raspberry-pi/WIRING_GUIDE.md`](raspberry-pi/WIRING_GUIDE.md) for full wiring instructions.

### Quick Setup
```bash
cd raspberry-pi
chmod +x install.sh
sudo ./install.sh
sudo nano /opt/smart-parking-sensor/.env   # set BACKEND_URL, DEVICE_SECRET
sudo systemctl start parking-sensor
sudo journalctl -u parking-sensor -f
```

> ⚠️ **HC-SR04 ECHO pin outputs 5V. Use a voltage divider before connecting to Raspberry Pi GPIO (3.3V max). See WIRING_GUIDE.md.**

---

## Testing
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Acceptance Tests
| # | Test | Result |
|---|------|--------|
| 1 | Empty lot assigns P1 first | ✅ `test_first_arrival_gets_p1` |
| 2 | Second arrival gets P2 | ✅ `test_second_arrival_gets_p2` |
| 3 | P1 vacated → next gets P1 | ✅ `test_vacancy_reuse` |
| 4 | Concurrent arrivals never share space | ✅ `test_concurrent_allocation` |
| 5 | Each visitor sees only their assignment | ✅ `test_privacy` |
| 6 | Assigned space blinks green | ✅ UI animation |
| 7 | QR opens correct institution app | ✅ `test_admin_qr` |
| 8 | Visitor can view destination + directions | ✅ `GET /api/parking/destination` |
| 9 | Simulator uses identical allocation logic | ✅ shared `allocation.py` |
| 10 | Full lot / expiry / disconnect handled | ✅ `test_full_lot`, expiry task |

---

## Production Deployment

```bash
cp .env.example .env.prod
# Edit .env.prod: strong SECRET_KEY, POSTGRES_PASSWORD, DOMAIN, DEVICE_SECRET
docker compose -f docker-compose.prod.yml up --build -d
```

### Security Checklist
- [ ] Change `SECRET_KEY` (run `openssl rand -hex 32`)
- [ ] Change admin password after first login
- [ ] Change `DEVICE_SECRET` for Pi sensor
- [ ] Set `CORS_ORIGINS` to your exact domain(s)
- [ ] Enable HTTPS (provide TLS cert in `nginx/certs/`)
- [ ] Restrict `/api/simulator/*` endpoints in production nginx config

---

## Optional Future Enhancements

| Feature | Description |
|---------|-------------|
| RFID | Replace or complement ultrasonic with RFID reader for vehicle ID |
| ANPR | Automatic number plate recognition for automatic session matching |
| BLE beacon | Mobile phone BLE beacon for proximity detection |
| SMS/Email alerts | Notify visitors of expiry or full lot |
| Multi-site | Multiple parking lots with separate QR codes |
| Payment integration | Paid parking with session billing |

---

## Project Structure

```
smart-parking/
├── backend/               FastAPI backend
│   ├── app/
│   │   ├── main.py       App entry point + startup
│   │   ├── config.py     All settings (env-based)
│   │   ├── database.py   Async SQLAlchemy + seeding
│   │   ├── auth.py       JWT auth + device auth
│   │   ├── models/       SQLAlchemy models
│   │   ├── schemas/      Pydantic v2 schemas
│   │   ├── routers/      FastAPI routers
│   │   ├── services/     Allocation, sessions, WebSocket hub
│   │   └── hardware/     Abstract + concrete GPIO adapters
│   ├── alembic/          DB migrations
│   ├── tests/            pytest tests
│   └── Dockerfile
├── frontend/              React PWA
│   ├── src/
│   │   ├── pages/        WelcomePage, DashboardPage, AdminDashboardPage, SimulatorPage
│   │   ├── components/   ParkingLayout, MapView, StatusBanner, Toast
│   │   ├── hooks/        useWebSocket, useSession, useAdminWebSocket
│   │   └── api/          Typed axios client
│   └── Dockerfile
├── raspberry-pi/          Pi sensor service
│   ├── sensor_service.py  Main sensor loop
│   ├── gpio_adapter.py    HC-SR04 + mock adapters
│   ├── install.sh         Automated install script
│   └── WIRING_GUIDE.md    ⚠️ MUST READ before hardware setup
├── docker-compose.yml     Development
├── docker-compose.prod.yml Production (PostgreSQL)
├── .env.example           Template for all config
└── README.md
```
