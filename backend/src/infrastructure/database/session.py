"""Async MySQL database engine and session factory."""

import time
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger

logger = get_logger("infrastructure.database")

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Obtain or initialize the global AsyncEngine instance."""
    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info(
            "initializing_mysql_async_engine",
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            pool_size=settings.DB_POOL_SIZE,
        )
        _engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=settings.DB_ECHO,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Obtain or initialize the session factory."""
    global _session_maker
    if _session_maker is None:
        engine = get_async_engine()
        _session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated async database session with auto-rollback."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> dict[str, str | float]:
    """Execute ping query against MySQL and measure latency."""
    engine = get_async_engine()
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            scalar = result.scalar()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if scalar == 1:
                return {"status": "healthy", "latency_ms": latency_ms}
            return {"status": "degraded", "error": "Unexpected scalar response"}
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {"status": "unhealthy", "error": str(exc)}
