"""FastAPI application factory: lifespan (Redis pool), CORS, routers, health."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis_client import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: open the shared Redis connection (best-effort — app still runs if down).
    try:
        client = await init_redis()
        await client.ping()
    except Exception:  # pragma: no cover - degrade gracefully if Redis is unavailable
        pass
    yield
    # Shutdown
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Customer Success Platform API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- API v1 routers ---
    from app.api.v1.routers import auth, customers, dashboard, interactions, users

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(interactions.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    return app


app = create_app()
