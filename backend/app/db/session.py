from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# SQLAlchemy async engine and sessionmaker
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.DB_ECHO,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e

@asynccontextmanager
async def get_db_connection():
    """
    Get a direct database connection using asyncpg.
    This is used for raw SQL queries.
    """
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        yield conn
    finally:
        await conn.close() 