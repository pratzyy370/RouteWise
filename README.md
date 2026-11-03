# RouteWise — Bengaluru-First Smart Urban Mobility Platform

[![CI Pipeline](https://github.com/routewise/routewise/actions/workflows/ci.yml/badge.svg)](https://github.com/routewise/routewise/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

RouteWise is a production-oriented, Bengaluru-first smart urban mobility platform that helps users find the optimal way to travel between any two locations in the city. It unifies ride-hailing comparisons across **Uber, Ola, Rapido, and Namma Yatri** with **multimodal transit routes combining Namma Metro, walking, auto-rickshaws, and cabs**.

---

## 🎯 Key Capabilities

- **Multimodal Journey Optimization**: Generates ordered journeys combining walking legs, Namma Metro transit, auto-rickshaw first/last mile, and direct ride-hailing.
- **Three Core Objectives**:
  - 💰 **Cheapest**: Minimizes total journey financial cost.
  - ⚡ **Fastest**: Minimizes overall estimated travel time.
  - ⚖️ **Balanced**: Computes normalized Pareto trade-offs across monetary cost, travel time, walking meters, and transfers.
- **Transparent Data Provenance & Freshness**:
  - Strictly distinguishes **live provider quotes**, **modelled estimates**, **historical observations**, and **synthetic demo fixtures**.
  - **Zero Fabrications Policy**: Never invents booking confirmations, live driver positions, or artificial transit timetables.
- **Explainable Recommendations**: Clear, contextual explanations why each route option was recommended over alternatives.
- **Geospatial Metro Discovery**: Real Bengaluru metro dataset covering Purple Line (*Challaghatta ↔ Whitefield*) and Green Line (*Nagasandra ↔ Silk Institute*) with Majestic interchange routing. PostGIS spatial support with Haversine fallback.
- **Fare Intelligence & Predictions**: Statistical moving-average baseline with dispersion bounds, confidence metrics, and sample-size validation.
- **Commute Savings & Alerts**: Counterfactual spending analysis against cheapest alternatives, automated price-drop alerts with cooldown protection.
- **Modern Security Architecture**: Argon2 password hashing, JWT bearer tokens, row-level ownership validation (IDOR defense), and structured JSON logging with correlation `X-Request-ID`.

---

## 🏗️ Architecture & Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (ASGI) | Async HTTP API, OpenAPI / Swagger documentation |
| **Data Validation** | Pydantic v2 & `pydantic-settings` | Strongly typed domain schemas and settings |
| **Database** | PostgreSQL + PostGIS (prod) / SQLite `aiosqlite` (dev) | Relational persistence and geospatial indexing |
| **ORM** | SQLAlchemy 2.x (asyncio) + Alembic | Declarative mapping, async session lifecycle, migrations |
| **Caching & Messaging** | Redis 7 | Quote caching, station lookups, and Celery broker |
| **Background Processing** | Celery + Celery Beat | Scheduled fare history aggregation and alert evaluation |
| **Security** | Argon2-cffi + Python-Jose | State-of-the-art password hashing and JWT token handling |
| **HTTP Client** | HTTPX (async) | External provider communication with timeouts |
| **Frontend** | Vanilla ES6+ & Responsive CSS (FastAPI served) | Integrated interactive mobility dashboard |

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites

- Python 3.12+ (or compatible 3.14)
- Git
- Docker & Docker Compose (optional, for full containerized stack)

### 2. Installation

Clone the repository and create a Python virtual environment:

```bash
git clone https://github.com/routewise/routewise.git
cd routewise

python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install ".[dev]"
```

### 3. Environment Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Secret key for JWT signing (min 32 chars) | Required |
| `DATABASE_URL` | Async database URL | `sqlite+aiosqlite:///./routewise.db` |
| `REDIS_URL` | Redis instance URL | `redis://localhost:6379/0` |
| `DEMO_MODE` | Whether to run in demo simulation mode | `true` |
| `POSTGIS_AVAILABLE` | Flag for PostGIS geography queries | `false` |

### 4. Running Database Migrations & Seeding

```bash
# Run database migrations
alembic upgrade head

# The application automatically seeds Bengaluru metro stations and demo observations on startup.
```

### 5. Starting the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at:
- **Interactive Web App**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 6. Starting Celery Background Workers (Optional)

```bash
# Start background worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start scheduled task beat
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## 🐳 Docker Deployment

To launch the complete production stack (FastAPI web app, PostGIS, Redis, Celery worker, and Celery beat) in Docker:

```bash
docker compose up --build -d
```

Verify services:

```bash
docker compose ps
docker compose logs -f web
```

---

## 🧪 Testing & Code Quality

### Run Test Suite

Run pytest with test coverage across unit and integration suites:

```bash
pytest -v --cov=app --cov-report=term-missing
```

### Run Code Formatting & Linting

```bash
ruff check app tests
ruff format --check app tests
```

---

## 📡 API Reference

### Health Probes
- `GET /health/live` — Liveness check verifying the HTTP worker process is responsive.
- `GET /health/ready` — Readiness check verifying database connectivity and Redis status.

### Journeys & Ride Comparison
- `POST /api/v1/journeys/compare` — Compare direct quotes across Uber, Ola, Rapido, and Namma Yatri concurrently.
- `POST /api/v1/journeys/optimize` — Full multimodal optimization (Metro + Walk + Auto/Cab) with explainable reasons.

### Metro Discovery
- `GET /api/v1/metro/nearby?lat=...&lng=...&radius_m=1500` — Find stations near coordinates.
- `GET /api/v1/metro/stations?line=purple` — List all stations with line filter.
- `GET /api/v1/metro/route?from_code=IDN&to_code=MGR` — Calculate station transit path, interchange, and fare.

### Authentication
- `POST /api/v1/auth/register` — Register a new account.
- `POST /api/v1/auth/login` — Authenticate and receive JWT tokens.
- `GET /api/v1/auth/me` — Retrieve current user profile.

### Saved Places (Protected)
- `GET /api/v1/places` — List user's saved places.
- `POST /api/v1/places` — Save a location (Home, Work, etc.).
- `PATCH /api/v1/places/{id}` — Update saved location (with ownership validation).
- `DELETE /api/v1/places/{id}` — Delete saved location.

### Fare Analytics & Alerts
- `POST /api/v1/fares/history` — Query 30-day historical observations by hour and day.
- `POST /api/v1/fares/predict` — Baseline price forecast with confidence intervals.
- `GET /api/v1/fares/alerts` — List user's active fare-drop alerts.
- `POST /api/v1/fares/alerts` — Create an automated fare alert with cooldown.

### Commute Spending & Savings
- `POST /api/v1/trips` — Log an actual completed trip and price paid.
- `GET /api/v1/trips` — Paginated list of completed trips.
- `GET /api/v1/trips/savings?days=30` — Savings analysis against cheapest historical alternatives.

---

## 📜 License

MIT License. Built for the citizens of Bengaluru.

