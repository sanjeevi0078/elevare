"""
Elevare Database Configuration
PostgreSQL with SQLAlchemy Async Engine for high concurrency.

Supports:
- AsyncEngine for non-blocking database operations
- Connection pooling for production workloads
- Fallback to SQLite for local development/testing
"""

import os
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE URL CONFIGURATION
# =============================================================================

# Read from environment - Docker Compose sets this
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://elevare:elevare_secret@localhost:5432/elevare_db"
)

# Sync URL for migrations and scripts (Alembic uses sync)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
if DATABASE_URL.startswith("postgresql+asyncpg"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2")

# SQLite fallback for local development without Docker
SQLITE_URL = "sqlite+aiosqlite:///./elevare.db"
SYNC_SQLITE_URL = "sqlite:///./elevare.db"

# Detect if we should use SQLite (for testing/local dev)
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = SQLITE_URL
    SYNC_DATABASE_URL = SYNC_SQLITE_URL
    logger.info("📦 Using SQLite (local development mode)")
else:
    logger.info(f"🐘 Using PostgreSQL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'configured'}")


# =============================================================================
# ASYNC ENGINE (Production - PostgreSQL)
# =============================================================================

def get_async_engine() -> AsyncEngine:
    """
    Create async engine with appropriate settings.
    
    - Uses AsyncAdaptedQueuePool for connection pooling
    - Configures pool size for concurrent requests
    """
    if USE_SQLITE:
        # SQLite async requires aiosqlite
        return create_async_engine(
            DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            future=True
        )
    
    return create_async_engine(
        DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
    )


# Create the async engine
async_engine = get_async_engine()

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# =============================================================================
# SYNC ENGINE (For Alembic migrations and scripts)
# =============================================================================

def get_sync_engine():
    """Create sync engine for migrations and initialization scripts."""
    if USE_SQLITE or SYNC_DATABASE_URL.startswith("sqlite"):
        return create_engine(
            SYNC_SQLITE_URL,
            connect_args={"check_same_thread": False},
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    
    return create_engine(
        SYNC_DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )


# Sync engine and session (for Alembic, scripts)
engine = get_sync_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# DECLARATIVE BASE
# =============================================================================

Base = declarative_base()


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI routes.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db():
    """
    Sync database session dependency (for backward compatibility).
    
    Use this for routes that haven't been migrated to async yet.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# DATABASE LIFECYCLE
# =============================================================================

async def init_db():
    """Initialize database tables (async version)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialized")


async def close_db():
    """Close database connections."""
    await async_engine.dispose()
    logger.info("✅ Database connections closed")


@asynccontextmanager
async def get_db_context():
    """Context manager for database sessions (useful in scripts)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

