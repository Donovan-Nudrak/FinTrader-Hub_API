# FinTrader Hub API

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Resend](https://img.shields.io/badge/Resend-Email-000000?logo=resend&logoColor=white)](https://resend.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![pytest](https://img.shields.io/badge/pytest-8.3+-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)



Production-oriented backend for personal trading portfolio management. Built with **FastAPI**, **PostgreSQL**, **Redis**, and **Celery**, featuring JWT authentication, real-time market data ingestion, risk analytics, alerting, and a modular domain architecture.

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Features](#features)
- [Project Metrics](#project-metrics)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Architectural Decisions](#architectural-decisions)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Development](#development)
- [Security](#security)
- [Current Scope](#current-scope)
- [Project Status](#project-status)
- [License](#license)

---

## Executive Summary

FinTrader Hub is a full-featured trading portfolio API designed for developers who want a serious, extensible backend foundation. It supports user registration, portfolio and position tracking, trade journaling, market price caching, news feeds, configurable alerts with email notifications, portfolio risk metrics, and encrypted storage of third-party API keys.

The stack is containerized with Docker Compose, runs database migrations automatically on API startup, and uses Celery Beat for scheduled background work. A shared ORM bootstrap ensures Celery workers and Alembic share the same SQLAlchemy mapper registry.

---

## Features


| Category           | Capabilities                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| **Authentication** | JWT Authentication · Refresh Tokens · Role-Based Access Control                                               |
| **Portfolio**      | Portfolio Management · Trade Tracking · Position Tracking · Portfolio Analytics                               |
| **Market Data**    | Asset Management · Market Data Aggregation · News Feed Aggregation                                            |
| **Alerts & Risk**  | Alert Engine · Email Notifications · Risk Analysis                                                            |
| **Security**       | API Key Encryption (Fernet) · Rate limiting on auth endpoints                                                 |
| **Infrastructure** | Automatic Database Migrations · Celery Background Tasks · Docker Deployment · OpenAPI / Swagger Documentation |


**Highlights:**

- **JWT Authentication** — access and refresh token flow with revocable sessions
- **Refresh Tokens** — hashed storage in PostgreSQL, rotation on `/auth/refresh`
- **Role-Based Access Control** — role model with user assignment at registration (user-scoped authorization)
- **Portfolio Management** — multi-portfolio CRUD, summaries, and performance views
- **Asset Management** — tradable asset catalog with search and provider metadata
- **Trade Tracking** — full trade journal per portfolio
- **Position Tracking** — open/closed positions with recalculation engine
- **Market Data Aggregation** — multi-provider price fetch (Finnhub, CoinGecko, Alpha Vantage)
- **News Feed Aggregation** — scheduled news ingestion and expiration
- **Alert Engine** — price and volume alerts with scheduled evaluation
- **Email Notifications** — alert delivery via Resend
- **Risk Analysis** — Sharpe, Sortino, drawdown, exposure, correlation, position sizing
- **Portfolio Analytics** — value, allocation, performance, and per-position PnL
- **API Key Encryption** — user provider keys encrypted at rest with Fernet
- **Automatic Database Migrations** — Alembic upgrade on API lifespan startup
- **Celery Background Tasks** — scheduled market sync and alert evaluation
- **Docker Deployment** — Compose profiles for development and production
- **OpenAPI / Swagger Documentation** — interactive docs at `/docs` and `/redoc`

---

## Project Metrics

Statistics derived from the current repository structure and test suite.


| Metric             | Value                                                                                                                        |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Domain modules     | **9** (`auth`, `portfolio`, `asset`, `trade`, `market`, `risk`, `alerts`, `dashboard`, `settings`)                           |
| Database tables    | **14** (SQLAlchemy models across 9 Alembic migrations)                                                                       |
| REST API endpoints | **57** (including `/health`)                                                                                                 |
| Automated tests    | **138** (unit + integration)                                                                                                 |
| Docker services    | **5** (`api`, `postgres`, `redis`, `celery_worker`, `celery_beat`)                                                           |
| Celery tasks       | **4** (`market.update_market_prices`, `market.update_news_feed`, `alerts.evaluate_alerts`, `health.ping`)                    |
| Technology stack   | **Python 3.12** · **FastAPI** · **PostgreSQL 16** · **Redis 7** · **Celery 5** · **SQLAlchemy 2** · **Alembic** · **Docker** |


---

## Technology Stack


| Layer          | Technology        | Role                                                      |
| -------------- | ----------------- | --------------------------------------------------------- |
| API            | FastAPI + Uvicorn | REST API, OpenAPI docs, lifespan hooks                    |
| ORM            | SQLAlchemy 2.x    | Models, repositories, session management                  |
| Migrations     | Alembic           | Schema versioning (`infrastructure/database/migrations/`) |
| Database       | PostgreSQL 16     | Primary data store                                        |
| Cache / Broker | Redis 7           | Price cache, Celery broker, rate limiting                 |
| Tasks          | Celery 5 + Beat   | Scheduled market updates and alert evaluation             |
| Auth           | JWT (HS256)       | Access + refresh token flow                               |
| Email          | Resend            | Alert notification delivery                               |
| Encryption     | Fernet            | User API key encryption at rest                           |
| Testing        | pytest + coverage | Unit and integration test suite                           |
| Containers     | Docker Compose    | Local dev and production profiles                         |


---

## Architecture

### System Overview

```mermaid
flowchart TB
    subgraph Clients
        HTTP[HTTP Clients / Swagger]
    end

    subgraph Docker["Docker Compose Stack"]
        API[FastAPI API<br/>:8000]
        CW[Celery Worker]
        CB[Celery Beat]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    subgraph External
        MH[Market Providers<br/>Finnhub · CoinGecko · Alpha Vantage]
        RS[Resend Email API]
    end

    HTTP --> API
    API --> PG
    API --> RD
    CW --> PG
    CW --> RD
    CB --> RD
    CW --> MH
    CW --> RS
    API --> MH
```



### Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant DB as PostgreSQL

    C->>A: POST /auth/register
    A->>DB: Create user (role: user)
    A-->>C: 201 UserResponse

    C->>A: POST /auth/login
    A->>DB: Validate credentials
    A-->>C: access_token + refresh_token

    C->>A: GET /portfolios (Bearer token)
    A->>A: Validate JWT, load user
    A->>DB: Query user portfolios
    A-->>C: 200 Portfolio list

    C->>A: POST /auth/refresh
    A->>DB: Validate refresh token hash
    A-->>C: New access_token
```



### Celery Task Flow

```mermaid
flowchart LR
    BEAT[Celery Beat] -->|schedule| BROKER[Redis Broker]
    BROKER --> WORKER[Celery Worker]
    WORKER --> BOOT[load_all_models]
    BOOT --> ORM[SQLAlchemy Registry]
    WORKER --> TASK{Task}
    TASK --> MP[market.update_market_prices]
    TASK --> NF[market.update_news_feed]
    TASK --> AL[alerts.evaluate_alerts]
    MP --> DB[(PostgreSQL)]
    NF --> DB
    AL --> DB
    AL --> EMAIL[Resend API]
```




| Task                          | Schedule (default) | Purpose                             |
| ----------------------------- | ------------------ | ----------------------------------- |
| `market.update_market_prices` | Every 5 min        | Fetch and persist asset prices      |
| `market.update_news_feed`     | Every 30 min       | Ingest and expire market news       |
| `alerts.evaluate_alerts`      | Every 5 min        | Evaluate active alerts, send emails |


### Application Startup Flow

```mermaid
flowchart TD
    START[Container / Process Start] --> ENV[Load env vars<br/>env_file / OS environment]
    ENV --> VAL[Startup validation<br/>JWT, Fernet, Resend, DB URL]
    VAL -->|fail| EXIT[SystemExit]
    VAL -->|ok| LIFE[Lifespan: apply_startup_migrations]
    LIFE --> WAIT[wait_for_database]
    WAIT --> ALEMBIC[alembic upgrade head]
    ALEMBIC --> READY[API ready — /health returns 200]
    READY --> CELERY[Celery worker/beat start<br/>after API healthy]
    CELERY --> MODELS[load_all_models + configure_mappers]
    MODELS --> TASKS[Tasks executable]
```



Celery workers depend on the API health check so the database schema is migrated before background tasks run.

---

## Architectural Decisions


| Decision                             | Rationale                                                                                                                                                                          |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FastAPI as HTTP layer**            | Async-capable, native OpenAPI generation, dependency injection, and Pydantic validation for a typed REST API.                                                                      |
| **PostgreSQL as primary datastore**  | ACID compliance for financial portfolio data, relational integrity across users, portfolios, trades, and positions.                                                                |
| **Redis as broker and cache**        | Single infrastructure component serving Celery message broker, result backend coordination, and market price caching.                                                              |
| **Celery for async tasks**           | Decouples long-running market fetches and alert evaluation from HTTP request lifecycle; Beat handles scheduling.                                                                   |
| **Alembic for automatic migrations** | Schema versioning applied on API startup (`apply_startup_migrations`) so workers never run against an unmigrated database.                                                         |
| **Shared ORM Bootstrap**             | `load_all_models()` in `infrastructure/database/model_loader.py` registers all SQLAlchemy mappers for FastAPI, Celery, and Alembic — preventing mapper registry errors in workers. |
| **Docker-first workflow**            | Multi-stage Dockerfile, Compose orchestration, health-gated startup order, and secrets injected at runtime (never baked into images).                                              |


---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+ and Docker Compose v2
- [Git](https://git-scm.com/)
- (Optional) Python 3.12 for local development outside Docker

### 1. Clone and configure

```bash
git clone https://github.com/Donovan-Nudrak/FinTrader-Hub_API.git
cd FinTrader-Hub_API
cp env.example .env
cp dockerignore .dockerignore
```

Edit `.env` and set **all required secrets** before first startup (see [Configuration](#configuration)).

### 2. Generate a Fernet encryption key

Required for encrypting user-stored API keys:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output into `API_KEY_ENCRYPTION_KEY` in your `.env` file.

### 3. Start the stack

```bash
docker compose up -d
```

On first boot, the API automatically waits for PostgreSQL, applies Alembic migrations to head, and exposes a health endpoint once the schema is ready. Celery worker and beat start only after the API reports healthy.

### 4. Verify

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

Expected response when fully ready:

```json
{
  "status": "healthy",
  "app": "FinTrader Hub",
  "environment": "development",
  "services": {
    "postgresql": "connected",
    "redis": "connected",
    "migrations": "applied",
    "schema": "ready"
  }
}
```

Interactive API documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Production profile

For a production-oriented compose file without development bind mounts:

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Configuration

Copy `[.env.example](.env.example)` to `.env`. **Never commit `.env` to version control.**

### Required External Services

The backend integrates with external services for market data and email delivery. Configure the variables below before first startup.


| Variable                 | Purpose                                                            | Required | Used by                           |
| ------------------------ | ------------------------------------------------------------------ | -------- | --------------------------------- |
| `DATABASE_URL`           | PostgreSQL connection string for all persistent data               | **Yes**  | API, Celery Worker, Alembic       |
| `REDIS_URL`              | Redis connection for cache, rate limiting, and Celery broker       | **Yes**  | API, Celery Worker, Celery Beat   |
| `JWT_SECRET_KEY`         | HS256 signing secret for access and refresh tokens (min. 32 chars) | **Yes**  | API                               |
| `API_KEY_ENCRYPTION_KEY` | Fernet key for encrypting user-stored provider API keys            | **Yes**  | API, Settings module              |
| `RESEND_API_KEY`         | Resend API authentication for alert email delivery                 | **Yes**  | API, Celery Worker (alerts)       |
| `RESEND_FROM_EMAIL`      | Verified sender address registered in Resend                       | **Yes**  | API, Celery Worker (alerts)       |
| `ALERT_EMAIL`            | Default recipient for system alert notifications                   | **Yes**  | API, Celery Worker (alerts)       |
| `FINNHUB_API_KEY`        | Finnhub market data API (stocks, forex)                            | No       | API, Celery Worker (market tasks) |
| `ALPHA_VANTAGE_API_KEY`  | Alpha Vantage fallback provider for market prices                  | No       | API, Celery Worker (market tasks) |
| `COINGECKO_API_KEY`      | CoinGecko crypto price provider                                    | No       | API, Celery Worker (market tasks) |
| `EXCHANGE_RATE_API_KEY`  | Exchange rate provider for currency conversion                     | No       | API, Celery Worker (market tasks) |


Market provider keys are optional individually — empty values disable that provider. At least one provider key is recommended for meaningful market data ingestion.

> **Startup validation:** The API refuses to start (unless `SKIP_STARTUP_VALIDATION=true`) if `JWT_SECRET_KEY`, `API_KEY_ENCRYPTION_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, or `ALERT_EMAIL` are missing or invalid.

### Required variables


| Variable                 | Description                                                                   |
| ------------------------ | ----------------------------------------------------------------------------- |
| `DATABASE_URL`           | PostgreSQL connection string (`postgresql://...`)                             |
| `JWT_SECRET_KEY`         | Signing secret, minimum 32 characters                                         |
| `API_KEY_ENCRYPTION_KEY` | Valid Fernet key (see [Getting Started](#2-generate-a-fernet-encryption-key)) |
| `RESEND_API_KEY`         | Resend API key for alert emails                                               |
| `RESEND_FROM_EMAIL`      | Verified sender address in Resend                                             |
| `ALERT_EMAIL`            | Default recipient for system alert notifications                              |


### Commonly used optional variables


| Variable                      | Default                | Description                      |
| ----------------------------- | ---------------------- | -------------------------------- |
| `REDIS_URL`                   | `redis://redis:6379/0` | Redis connection                 |
| `CELERY_BROKER_URL`           | `redis://redis:6379/0` | Celery message broker            |
| `MARKET_PRICE_UPDATE_MINUTES` | `5`                    | Beat interval for price updates  |
| `NEWS_FEED_UPDATE_MINUTES`    | `30`                   | Beat interval for news ingestion |
| `SKIP_AUTO_MIGRATIONS`        | `false`                | Set `true` in tests/CI only      |
| `SKIP_STARTUP_VALIDATION`     | `false`                | Set `true` in tests/CI only      |


Market provider keys (`FINNHUB_API_KEY`, `COINGECKO_API_KEY`, etc.) are optional; empty values disable the corresponding provider.

### How secrets reach containers

- **Docker image:** `.env` is excluded via `.dockerignore` and verified at build time. Secrets are **never baked into image layers**.
- **Runtime:** `docker-compose.yml` injects variables through `env_file: .env` and service `environment` blocks.
- **Local development:** the bind mount (`.:/app`) makes your host `.env` visible inside containers at runtime only — this does not affect published images.

---

## Usage

### Health endpoint

```bash
curl http://localhost:8000/health
```

Returns **503** until PostgreSQL, Redis, migrations, and essential tables are ready.

### Swagger / OpenAPI


| URL             | Description    |
| --------------- | -------------- |
| `/docs`         | Swagger UI     |
| `/redoc`        | ReDoc          |
| `/openapi.json` | OpenAPI schema |


### Authentication

Register and obtain tokens:

```bash
# Register
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@example.com","username":"devuser","password":"SecurePass123!"}'

# Login
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@example.com","password":"SecurePass123!"}'
```

Use the `access_token` from the login response:

```bash
export TOKEN="<access_token>"

curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Protected endpoint example

```bash
curl -s http://localhost:8000/portfolios \
  -H "Authorization: Bearer $TOKEN"
```

Unauthenticated requests to protected routes return **401 Unauthorized**.

### Public vs protected routes


| Access    | Examples                                                                                                                  |
| --------- | ------------------------------------------------------------------------------------------------------------------------- |
| Public    | `GET /health`, `GET /assets`, `GET /market/prices/`*, `GET /market/news/*`                                                |
| Protected | `POST /assets`, `POST /market/prices/fetch`, all `/portfolios/*`, `/trades/*`, `/alerts/*`, `/settings/*`, `/dashboard/*` |


---

## Project Structure

```
FTHub_Full_BACK/
├── app/                    # FastAPI application factory and health router
│   ├── factory.py          # App creation, lifespan, router registration
│   └── routers/
├── core/                   # Cross-cutting concerns
│   ├── config/             # Settings, startup validation
│   ├── security/           # JWT, password hashing
│   ├── middleware/         # Rate limiting, request logging
│   └── exceptions/         # Global error handlers
├── modules/                # Domain modules (vertical slices)
│   ├── auth/               # Registration, login, JWT, roles
│   ├── portfolio/          # Portfolios, analytics
│   ├── asset/              # Tradable assets catalog
│   ├── trade/              # Trades and positions
│   ├── market/             # Prices, news, provider integration
│   ├── risk/               # Sharpe, Sortino, drawdown, exposure
│   ├── alerts/             # Alert rules, evaluation, notifications
│   ├── dashboard/          # Aggregated dashboard metrics
│   └── settings/           # User settings, encrypted API keys
├── infrastructure/         # Technical infrastructure
│   ├── database/           # Base models, sessions, migrations, ORM bootstrap
│   ├── tasks/              # Celery app, market and alert tasks
│   └── notifications/      # Resend email client
├── tests/                  # Unit and integration tests
├── docker/
│   └── Dockerfile          # Multi-stage production image
├── docker-compose.yml      # Development stack (bind mount)
├── docker-compose.prod.yml # Production stack (no bind mount)
├── alembic.ini
├── requirements.txt
├── .env.example            # Environment template (safe to commit)
└── LICENSE                 # MIT License
```

Each domain module follows a consistent layout: `models/`, `repositories/`, `services/`, `routers/`, `schemas/`, and `dependencies.py`.

---

## Development

### Run tests

With PostgreSQL and Redis available on `localhost`:

```bash
docker compose up -d postgres redis
docker compose build api

docker run --rm --network host -v "$(pwd):/app" -w /app \
  -e SKIP_STARTUP_VALIDATION=true \
  -e SKIP_AUTO_MIGRATIONS=true \
  -e DATABASE_URL=postgresql://fintrader:fintrader_secret@localhost:5432/fintraderhub \
  fthub_full_back-api pytest -o addopts= -q
```

Integration tests apply migrations once per session via `tests/integration/conftest.py`.

### Coverage (default pytest config)

```bash
docker run --rm --network host -v "$(pwd):/app" -w /app \
  -e SKIP_STARTUP_VALIDATION=true \
  -e SKIP_AUTO_MIGRATIONS=true \
  -e DATABASE_URL=postgresql://fintrader:fintrader_secret@localhost:5432/fintraderhub \
  fthub_full_back-api pytest
```

Coverage thresholds are enforced for core domain packages (≥ 80%).

### Database migrations

Migrations run automatically on API startup. For manual control:

```bash
# Inside API container
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose exec api alembic history
```

### Common commands

```bash
# Rebuild images (secrets excluded from layers)
docker compose build --no-cache

# View logs
docker compose logs -f api celery_worker celery_beat

# Celery worker health
docker compose exec celery_worker celery -A infrastructure.tasks.celery_app inspect ping

# Trigger a task manually
docker compose exec celery_worker celery -A infrastructure.tasks.celery_app call market.update_market_prices
```

---

## Security

### Secret management


| Practice             | Implementation                                                               |
| -------------------- | ---------------------------------------------------------------------------- |
| No secrets in Git    | `.env` listed in `.gitignore`                                                |
| No secrets in images | `.dockerignore` excludes `.env`; Dockerfile fails build if `.env` is present |
| Runtime injection    | Compose `env_file` supplies variables to running containers                  |
| Encrypted API keys   | User provider keys stored with Fernet (`API_KEY_ENCRYPTION_KEY`)             |


### JWT authentication

- **Algorithm:** HS256
- **Access token:** short-lived (default 30 minutes)
- **Refresh token:** stored as SHA-256 hash in PostgreSQL, revocable on logout
- Protected routes use `Authorization: Bearer <access_token>`

### Roles

Users are assigned a `role_id` at registration (default: `user`). The legacy `admin` role was removed from runtime; only the standard `user` role is actively used. Role-based route guards are not implemented — authorization is user-scoped (users access only their own portfolios, alerts, and settings).

### API keys

Users may store third-party market provider keys via `/settings/api-keys`. Keys are encrypted at rest and never returned in plaintext through the API.

### Rate limiting

Authentication endpoints are rate-limited (`AUTH_RATE_LIMIT_PER_MINUTE`, default 10 requests/minute per IP).

---

## Current Scope

This backend is a **personal portfolio management API** — not a trading execution platform. The scope below defines what the project delivers today versus what is intentionally excluded.

### Included


| Area                      | Description                                                       |
| ------------------------- | ----------------------------------------------------------------- |
| **Portfolio management**  | Multi-portfolio CRUD, summaries, dashboard snapshots              |
| **Trade journaling**      | Record and manage trades per portfolio                            |
| **Asset tracking**        | Catalog of tradable assets with search and metadata               |
| **Market data ingestion** | Scheduled price fetching from multiple providers                  |
| **News aggregation**      | Scheduled news feed ingestion and expiration                      |
| **Alerting**              | Configurable price/volume alerts with email notifications         |
| **Analytics**             | Portfolio value, allocation, performance, and PnL metrics         |
| **Risk evaluation**       | Sharpe, Sortino, drawdown, exposure, correlation, position sizing |


### Not included


| Area                              | Description                                                |
| --------------------------------- | ---------------------------------------------------------- |
| **Broker integrations**           | No connection to brokerage accounts or custodians          |
| **Order execution**               | No buy/sell order placement                                |
| **Algorithmic trading**           | No strategy engines or automated trading logic             |
| **Real-money trading automation** | No live trade execution or fund movement                   |
| **Exchange connectivity**         | No direct WebSocket or REST links to exchanges for trading |


---

## Project Status

The backend is **stable, functional, fully dockerized, and covered by 138 automated tests**. All features defined for the implemented development phases (1–13) are complete. The API, Celery workers, database migrations, and health checks operate end-to-end in Docker Compose.

### Implemented modules


| Module        | Capabilities                                                          |
| ------------- | --------------------------------------------------------------------- |
| **Auth**      | Register, login, logout, refresh, profile (`/auth/me`)                |
| **Portfolio** | CRUD portfolios, summary, performance analytics                       |
| **Asset**     | Asset catalog, search, create/update (auth required for writes)       |
| **Trade**     | Trade journal per portfolio                                           |
| **Position**  | Open/closed positions, position engine                                |
| **Market**    | Price cache, news feed, multi-provider fetch                          |
| **Risk**      | Sharpe, Sortino, max drawdown, exposure, correlation, position sizing |
| **Alerts**    | Price/volume alerts, email notifications via Resend                   |
| **Dashboard** | Aggregated portfolio overview                                         |
| **Settings**  | User preferences, encrypted API key management                        |


### Supported functionality

- Automatic database migrations on API startup
- Deep health check (DB, Redis, migrations, schema tables)
- Background market price and news synchronization
- Scheduled alert evaluation with email delivery
- Shared ORM bootstrap for Celery and Alembic
- Docker Compose for local development and production profiles
- 138 automated tests (unit + integration)

### Out of scope (not implemented)

- Change password / update user profile (read-only profile exists)
- Trade import / export
- Data backup / restore
- Frontend application
- Admin panel or role-based access control beyond user scoping

---

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 FinTrader Hub Contributors.
