from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import REPOSITORY_ROOT
from app.db.models import Base


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Database:
    """Owns the SQLAlchemy engine and request-scoped session factory."""

    def __init__(self, database_url: str) -> None:
        self.url = normalize_database_url(database_url)
        if self.url.startswith("sqlite"):
            Path(REPOSITORY_ROOT / ".local").mkdir(parents=True, exist_ok=True)
        connect_args = {"timeout": 15} if self.url.startswith("sqlite") else {}
        self.engine: AsyncEngine = create_async_engine(
            self.url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite")

    async def initialize_local_schema(self) -> None:
        """Create portable tables only for the documented SQLite development fallback."""
        if not self.is_sqlite:
            return
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
