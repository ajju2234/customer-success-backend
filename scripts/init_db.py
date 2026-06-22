"""Dev convenience: create all tables from the models against DATABASE_URL.

Use this for quick local runs (e.g. SQLite). In production / Docker the schema is
managed by Alembic migrations (`alembic upgrade head`), not this script.
"""
import asyncio

from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401  (register models on Base.metadata)


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✓ tables created")


if __name__ == "__main__":
    asyncio.run(main())
