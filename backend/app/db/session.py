from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings

settings = get_settings()

echo=False  # set True only while debugging SQL
if settings.is_development and settings.app_env == "debug_sql":
    echo = True
engine_kwargs = {"echo": echo}
if not settings.database_url.startswith("sqlite"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

sync_kwargs = {}
if settings.database_url_sync.startswith("sqlite"):
    sync_kwargs["connect_args"] = {"check_same_thread": False}
else:
    sync_kwargs["pool_pre_ping"] = True

sync_engine = create_engine(settings.database_url_sync, **sync_kwargs)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    from app.models import Base
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight column patches for existing SQLite DBs (create_all won't ALTER)
        patches = [
            ("staff", "monthly_salary", "ALTER TABLE staff ADD COLUMN monthly_salary FLOAT DEFAULT 0"),
            ("staff", "branch_id", "ALTER TABLE staff ADD COLUMN branch_id CHAR(36)"),
            ("students", "training_days_total", "ALTER TABLE students ADD COLUMN training_days_total INTEGER DEFAULT 180"),
            ("students", "training_days_remaining", "ALTER TABLE students ADD COLUMN training_days_remaining INTEGER DEFAULT 180"),
            ("students", "branch_id", "ALTER TABLE students ADD COLUMN branch_id CHAR(36)"),
            ("punch_events", "branch_id", "ALTER TABLE punch_events ADD COLUMN branch_id CHAR(36)"),
        ]
        for table, column, ddl in patches:
            try:
                await conn.execute(text(ddl))
            except Exception:
                pass  # column already exists
