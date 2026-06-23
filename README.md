# Customer Success Platform — Backend

FastAPI backend for an AI-powered Customer Success platform: manage customers and interactions,
generate structured **AI insights** from meeting notes, and serve a Redis-cached metrics dashboard —
with JWT auth and role-based access control.

> This is the **backend** repository. The frontend lives in a separate repo:
> **`customer-success-frontend`**. This repo also hosts the `docker-compose.yml` that orchestrates
> the full stack (Postgres + Redis + backend + frontend).

---

## 🚀 Live Demo & Evaluator Guide

| | URL |
|---|---|
| **App (frontend)** | https://customer-success-frontend-iota.vercel.app |
| **API + Swagger docs** | `https://<railway-backend-url>/docs` |

Stack in production: **Vercel** (Next.js) · **Railway** (FastAPI) · **Supabase** (PostgreSQL) · **Upstash** (Redis).

### 🔑 Demo credentials — every account's password is `Test@1234`

| Role | Email | What they can do |
|------|-------|------------------|
| **Admin** | `sarah.chen@csp.com` | Everything + **Users** management screen + org-wide dashboard |
| **Manager** | `michael.rodriguez@csp.com` | All customers & interactions, org-wide dashboard (no user management) |
| **Manager** | `priya.sharma@csp.com` | — |
| **Manager** | `david.thompson@csp.com` | — |
| **CSM** | `emily.watson@csp.com` | Only **their own** customers & interactions; dashboard scoped to them |
| **CSM** | `james.park@csp.com` | — |
| **CSM** | `aisha.khan@csp.com` | — |
| **CSM** | `carlos.mendez@csp.com` | — |
| **CSM** | `nina.petrov@csp.com` | — |

The database is pre-seeded with **14 customers** and **19 interactions** (with AI insights) across the CSMs, so the dashboard is populated. Re-seed anytime with `python -m scripts.seed`.

### 👀 How to see RBAC in action
1. **Log in as the Admin** (`sarah.chen@csp.com`) → sidebar shows a **Users** link; you see **all** customers/interactions and an org-wide dashboard. Open **Users** to change anyone's role / activate-deactivate.
2. **Log in as a Manager** (`michael.rodriguez@csp.com`) → org-wide data & dashboard, but **no Users link** (try opening `/users` → access denied; the API returns `403`).
3. **Log in as a CSM** (`emily.watson@csp.com`) → you only see **your own** customers & interactions, and the dashboard counts are **scoped to you** — a different CSM (`aisha.khan@csp.com`) sees a different set. This proves the ownership isolation.

### 🛡️ RBAC matrix (enforced server-side)

| Capability | Admin | Manager | CSM |
|---|:---:|:---:|:---:|
| Manage users & assign roles | ✅ | ❌ | ❌ |
| View/manage **all** customers & interactions | ✅ | ✅ | ❌ (own only) |
| Create/edit/delete own customers & interactions | ✅ | ✅ | ✅ |
| Dashboard scope | org-wide | org-wide | own accounts |
| Generate AI insights | ✅ | ✅ | ✅ |

Authorization is enforced in a FastAPI `require_roles(...)` dependency **plus** `owner_id` ownership checks in the service layer — the UI simply reflects it (and hides the Users link for non-admins).

---

## ✨ Features

- **Auth & RBAC** — register / login / refresh / profile with JWT (short-lived access token + httpOnly refresh cookie). Roles: `admin`, `manager`, `csm`.
- **Customers** — full CRUD, search, status filter, pagination, ownership scoping.
- **Interactions** — log meetings/calls/emails/notes per customer, with filters.
- **AI insights** — summary, sentiment, action items, risks via an OpenAI-compatible LLM (Google Gemini / OpenRouter / OpenAI), with strict-JSON parsing, one retry, and a graceful heuristic **fallback** so the app never breaks.
- **Dashboard** — KPIs + chart data, role-scoped.
- **Redis caching** — dashboard metrics cached with a TTL and **invalidated on every write**.

## 🧱 Stack

Python · FastAPI · async SQLAlchemy 2.0 · Alembic · Pydantic v2 · PostgreSQL 16 · Redis 7 ·
OpenRouter · JWT + bcrypt · Docker.

---

## 🚀 Quick Start — full stack via Docker Compose

The compose file builds the frontend from a **sibling folder**, so clone both repos next to each
other:

```bash
mkdir customer-success-platform && cd customer-success-platform
git clone https://github.com/ajju2234/customer-success-backend.git  backend
git clone https://github.com/ajju2234/customer-success-frontend.git frontend

cd backend
cp .env.example .env          # set JWT_SECRET and (optionally) OPENROUTER_API_KEY
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **API + Swagger:** http://localhost:8000/docs

Migrations run automatically on startup (`alembic upgrade head`).
> The compose maps Postgres to host port **5433** to avoid clashing with a local Postgres on 5432.

---

## ⚙️ Environment

See [`.env.example`](.env.example). Notable: `JWT_SECRET`, `OPENROUTER_API_KEY`
(empty → heuristic fallback), `OPENROUTER_MODEL`, `DASHBOARD_CACHE_TTL_SECONDS`, `CORS_ORIGINS`.

## 🔐 RBAC

| Capability | admin | manager | csm |
|---|:---:|:---:|:---:|
| Customers/interactions CRUD | all | all | **own only** |
| Dashboard scope | org-wide | org-wide | own customers |

Enforced server-side via a `require_roles` dependency + `owner_id` ownership checks in services.

## 🤖 AI Integration (`app/services/ai_service.py`)

System prompt pins a strict JSON contract → response parsed + validated against a Pydantic schema →
one retry on failure → deterministic **fallback** (`status="fallback"`) when the LLM is unavailable
or no API key is set. The API never errors on AI failure.

## ⚡ Caching (`app/services/cache.py`)

Dashboard metrics cached in Redis under `dashboard:metrics:{scope}` with a TTL; every
customer/interaction/insight write invalidates the affected keys. The response carries a `cached`
flag. Degrades gracefully if Redis is down.

---

## 🧪 Tests

```bash
virtualenv .venv && . .venv/bin/activate   # or python -m venv
pip install -r requirements.txt
pytest                                      # 18 tests: auth, RBAC, CRUD, AI, cache
```

## 💻 Local dev (without Docker)

```bash
pip install -r requirements.txt
# Postgres: alembic upgrade head ; or SQLite quick run:
DATABASE_URL="sqlite+aiosqlite:///./dev.db" python -m scripts.init_db
DATABASE_URL="sqlite+aiosqlite:///./dev.db" uvicorn app.main:app --reload
```

## 📁 Structure

```
app/
├── core/      # config, security (JWT/hash), deps (RBAC guard), redis client
├── db/        # async engine/session, declarative base + mixins
├── models/    # User, Customer, Interaction, AIInsight
├── schemas/   # Pydantic request/response models
├── api/v1/    # routers: auth, customers, interactions, dashboard
└── services/  # business logic, ai_service, cache, dashboard
alembic/       # migrations
tests/         # pytest suite
```

## 📝 Design notes

Stateless JWT + refresh rotation · thin routers / logic in services · ownership-scoped access ·
AI never blocks the product · short-TTL cache + explicit write-invalidation · portable column types
(`Uuid`, `JSONB`→`JSON` variant) so the same models run on Postgres (prod) and SQLite (tests).
