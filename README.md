# Customer Success Platform — Backend

An AI-powered Customer Success platform: manage customers and the interactions you have with them
(meetings, calls, emails, notes), automatically turn meeting notes into structured **AI insights**
(summary · sentiment · action items · risks), and view a **Redis-cached metrics dashboard** — all
behind JWT auth with **role-based access control** (admin / manager / csm).

> This is the **backend** repository (FastAPI). The frontend (Next.js) lives in a separate repo:
> **[`customer-success-frontend`](https://github.com/ajju2234/customer-success-frontend)**.
> This repo also hosts the `docker-compose.yml` that runs the **whole stack** locally
> (Postgres + Redis + backend + frontend) with one command.

---

## 🚀 Live demo

| | URL |
|---|---|
| **App (use this)** | **https://customerorbit.vercel.app** |
| **API + interactive Swagger docs** | `https://<YOUR-RAILWAY-APP>.up.railway.app/docs` |

Production stack: **Vercel** (Next.js frontend) · **Railway** (FastAPI backend) · **Supabase** (PostgreSQL) · **Upstash** (Redis) · **Google Gemini Flash-Lite** (AI).

### 🔑 Demo credentials — every account's password is `Test@1234`

| Role | Email | What they can do |
|------|-------|------------------|
| **Admin** | `sarah.chen@csp.com` | Everything + org-wide dashboard. Sees **all** customers & interactions. |
| **Manager** | `michael.rodriguez@csp.com` | All customers & interactions + org-wide dashboard. |
| **Manager** | `priya.sharma@csp.com` | (same as above) |
| **Manager** | `david.thompson@csp.com` | (same as above) |
| **CSM** | `emily.watson@csp.com` | Only **their own** customers & interactions; dashboard scoped to them. |
| **CSM** | `james.park@csp.com` | (own data only) |
| **CSM** | `aisha.khan@csp.com` | (own data only) |
| **CSM** | `carlos.mendez@csp.com` | (own data only) |
| **CSM** | `nina.petrov@csp.com` | (own data only) |

The database is pre-seeded with **13 customers** and **18 interactions** (each with an AI insight),
spread across the 5 CSMs, so every dashboard is populated. Re-seed anytime with `python -m scripts.seed`.

### 👀 The 60-second evaluator tour

1. **Log in as the Admin** (`sarah.chen@csp.com` / `Test@1234`).
   You see **all 13 customers**, every interaction, and an **org-wide dashboard**.
2. **Open a customer → an interaction with notes.** The **AI Insight panel** shows a generated
   summary, a sentiment badge, action items and risks. Hit **Regenerate** to call the LLM again.
3. **Create a new interaction** with some meeting notes → an insight is generated **on create**.
4. **Log out, log in as a CSM** (`emily.watson@csp.com`).
   Now you see **only Emily's customers** (Acme, Globex, Cyberdyne) and her dashboard counts differ.
   A different CSM (`aisha.khan@csp.com`) sees a completely different set — this is ownership isolation.
5. **Try to reach another CSM's data.** The UI won't link to it, and the API returns **`403`**.
   Managers/Admin can see everything; CSMs can't. That's RBAC enforced server-side.

---

## 🛡️ Role-based access control (enforced server-side)

| Capability | Admin | Manager | CSM |
|---|:---:|:---:|:---:|
| View/manage **all** customers & interactions | ✅ | ✅ | ❌ — **own only** |
| Create / edit / delete own records | ✅ | ✅ | ✅ |
| Generate / regenerate AI insights | ✅ | ✅ | ✅ |
| Dashboard scope | org-wide | org-wide | own accounts |

Authorization is **never** trusted from the client. It is enforced in two layers:

- A FastAPI dependency **`require_roles(...)`** gates role-restricted routes (returns `403` otherwise).
- The **service layer** applies `owner_id == current_user.id` scoping for CSMs on every query and
  mutation, so a CSM literally cannot read or modify another owner's rows (cross-owner access → `403`).

The frontend mirrors this (it hides links a role can't use), but the server is the source of truth.

---

## ✨ What's built — feature by feature

- **Auth** — register / login / refresh / logout / profile. Short-lived **JWT access token** (sent as
  `Authorization: Bearer`) + long-lived **refresh token in an httpOnly cookie**; the access token is
  silently refreshed on `401`. Passwords hashed with **bcrypt**.
- **Forgot / reset password** — `POST /auth/forgot-password` issues a signed, 30-minute reset token
  and **emails a reset link** (SMTP). With no SMTP configured (local dev) the token is returned in the
  response so the flow still works. `POST /auth/reset-password` consumes the token and sets the new password.
- **Customers** — full CRUD with **search** (`q`), **status filter**, and **pagination**; ownership-scoped for CSMs.
- **Interactions** — log meetings / calls / emails / notes against a customer, with filters; each
  interaction can carry one AI insight (1:1).
- **AI insights** — turn `notes` into `{summary, sentiment, action_items[], risks[]}` via an
  OpenAI-compatible LLM, with strict-JSON parsing, **one retry**, and a deterministic **heuristic
  fallback** so the product never breaks. Generated **on interaction create** and via a **regenerate** endpoint.
- **Dashboard** — KPI cards + chart data (status breakdown, sentiment split, at-risk count, recent
  activity), **role-scoped**.
- **Redis caching** — the expensive dashboard aggregation is cached with a **TTL** and **invalidated on every write**.

---

## 🏗️ How it's built — architecture & request flow

**Layered, thin-router architecture** — routers do HTTP, services hold the logic:

```
HTTP request
   │
   ▼
api/v1/routers/*          ← FastAPI routers: parse/validate (Pydantic), status codes
   │   depends on
   ▼
core/deps.py              ← get_db (async session), get_current_user (decodes JWT),
   │                         require_roles(...) (RBAC guard)
   ▼
services/*                ← business logic: ownership scoping, AI calls, cache, aggregation
   │
   ▼
models/*  (SQLAlchemy)     ← async SQLAlchemy 2.0, mapped to Postgres
   │
   ▼
PostgreSQL  +  Redis (cache)  +  LLM (AI insights)
```

### Data model (UUID PKs, timestamps on every table)

- **users** — `id, name, email (unique), hashed_password, role (admin|manager|csm), is_active, …`
- **customers** — `id, name, company, email, phone, status (prospect|active|at_risk|churned), health_score, owner_id → users, …`
- **interactions** — `id, customer_id → customers, user_id → users (author), type (meeting|call|email|note), title, notes, meeting_date, …`
- **ai_insights** (1:1 with interaction) — `id, interaction_id (unique), summary, sentiment, action_items (JSON[]), risks (JSON[]), model, status (success|fallback), created_at`

Models use portable column types (`Uuid`, JSON) so the **same models run on Postgres (prod) and SQLite (tests)**.

### Auth flow (secure session)

1. `login` → returns an **access token** (kept in memory / Redux on the client) and sets a
   **refresh token** in an **httpOnly cookie** (`SameSite`/`Secure` are env-driven for cross-domain prod).
2. Every API call sends `Authorization: Bearer <access>`.
3. On a `401`, the client calls **`/auth/refresh`** (cookie-based) once, gets a fresh access token, and
   retries — the refresh token is **rotated** on each use. If refresh fails → logout.

### AI flow (`app/services/ai_service.py`)

1. Build a system prompt that pins a **strict JSON contract** and call the LLM's
   `chat/completions` with `response_format=json_object`, temperature `0.2`.
2. Parse `choices[0].message.content` → validate against the **`InsightData`** Pydantic schema.
   The schema is **tolerant of LLM quirks**: sentiment is normalised case-insensitively
   (`"Negative"` → `negative`, unknown → `neutral`) and null/string lists are coerced to arrays —
   so a usable answer is never discarded as a "failure".
3. On timeout / non-200 / bad JSON / schema mismatch → **retry once** → otherwise return a
   **heuristic fallback** (`status="fallback"`, neutral sentiment, keyword-derived summary). The API
   never errors on AI failure, and the UI shows a Regenerate affordance.
4. The provider is **env-driven** (any OpenAI-compatible API): Gemini, OpenRouter, or OpenAI — swap by
   changing `AI_BASE_URL` / `AI_MODEL` only.

### Caching flow (`app/services/cache.py`)

- Dashboard metrics are cached in Redis under **`dashboard:metrics:{scope}`** (`scope` = `all` for
  admin/manager, `user:{id}` for a CSM) with a **TTL** (`DASHBOARD_CACHE_TTL_SECONDS`, default 60s).
- Every customer / interaction / insight **write invalidates** the affected keys, so data is never
  stale after a mutation. The response carries a `cached` flag. If Redis is down, it **degrades gracefully** (just computes live).

---

## 🧱 Tech stack

Python · **FastAPI** · **async SQLAlchemy 2.0** (asyncpg) · **Alembic** · **Pydantic v2** ·
PostgreSQL 16 · Redis 7 · **JWT + bcrypt** · `httpx` (LLM) · **Google Gemini Flash-Lite** · Docker.

---

## 🚀 Run the whole stack locally (Docker Compose)

The compose file builds the frontend from a **sibling folder**, so clone both repos next to each other:

```bash
mkdir customer-success-platform && cd customer-success-platform
git clone https://github.com/ajju2234/customer-success-backend.git  backend
git clone https://github.com/ajju2234/customer-success-frontend.git frontend

cd backend
cp .env.example .env          # set JWT_SECRET; AI key optional (see below)
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **API + Swagger:** http://localhost:8000/docs

Migrations run automatically on startup (`alembic upgrade head`). Seed demo data with
`docker compose exec backend python -m scripts.seed`.
> Compose maps Postgres to host port **5433** to avoid clashing with a local Postgres on 5432.

---

## ⚙️ Environment

See [`.env.example`](.env.example) for the full, documented list. The important ones:

| Var | Purpose |
|---|---|
| `DATABASE_URL` | async Postgres URL (`postgresql+asyncpg://…`; add `?ssl=require` on Supabase) |
| `REDIS_URL` | Redis connection (optional — app runs without it) |
| `JWT_SECRET` | signing secret for access/refresh/reset tokens |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | `true` / `none` for cross-domain prod (Vercel + Railway) |
| `AI_API_KEY` / `AI_MODEL` / `AI_BASE_URL` | LLM provider (empty key → heuristic fallback) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | password-reset emails |
| `FRONTEND_URL` | base URL used to build the reset link |
| `CORS_ORIGINS` | comma-separated allowed origins (the frontend) |

### AI provider (recommended: Gemini Flash-Lite — cheapest + most generous free quota)

```env
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
AI_MODEL=gemini-flash-lite-latest
AI_API_KEY=<your-google-ai-studio-key>
```

Leave `AI_API_KEY` empty to use the built-in heuristic fallback (the app still works end-to-end).

---

## 🧪 Tests

```bash
virtualenv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest                              # 26 tests: auth, RBAC denial, ownership, AI parse/fallback, cache hit+invalidation
```

Tests run against in-memory SQLite and mock the LLM, so they're fast and need no external services.

## 💻 Local dev without Docker

```bash
pip install -r requirements.txt
# quick SQLite run (no Postgres needed):
DATABASE_URL="sqlite+aiosqlite:///./dev.db" python -m scripts.init_db
DATABASE_URL="sqlite+aiosqlite:///./dev.db" uvicorn app.main:app --reload
```

## 📁 Structure

```
app/
├── core/      # config (pydantic-settings), security (JWT/bcrypt), deps (DB + RBAC), email, redis
├── db/        # async engine/session, declarative base + timestamp mixins
├── models/    # User, Customer, Interaction, AIInsight + enums
├── schemas/   # Pydantic request/response models (+ tolerant InsightData)
├── api/v1/    # routers: auth, customers, interactions, dashboard
└── services/  # auth, customer, interaction, ai_service, cache, dashboard
alembic/       # migrations
scripts/       # seed.py (demo data), init_db.py
tests/         # pytest suite
```

## 📝 Design notes

Stateless JWT + refresh rotation · thin routers, logic in services · ownership-scoped access ·
**AI never blocks the product** (retry → heuristic fallback) · short-TTL cache + explicit
write-invalidation · provider-agnostic LLM config · portable column types so the same models run on
Postgres (prod) and SQLite (tests).
