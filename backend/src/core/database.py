"""Подключение к PostgreSQL через SQLAlchemy (async)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# Одно подключение к БД на всё приложение.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=15,
    max_overflow=10,
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependency: создаёт новую сессию на каждый запрос."""
    async with async_session_factory() as session:
        yield session
