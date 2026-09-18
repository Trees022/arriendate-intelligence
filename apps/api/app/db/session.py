from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import text
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
        connect_args = {"timeout": 15} if self.url.startswith("sqlite") else None
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
            property_columns = {
                row[1]
                for row in (await connection.execute(text("pragma table_info(properties)")))
            }
            matching_columns = {
                row[1]
                for row in (await connection.execute(text("pragma table_info(matching_runs)")))
            }
            target_columns = {
                row[1]
                for row in (
                    await connection.execute(text("pragma table_info(publication_targets)"))
                )
            }
            job_columns = {
                row[1]
                for row in (await connection.execute(text("pragma table_info(publication_jobs)")))
            }
            publication_columns = {
                row[1]
                for row in (await connection.execute(text("pragma table_info(publications)")))
            }
            if "embedding_provider" not in property_columns:
                await connection.execute(
                    text("alter table properties add column embedding_provider varchar(80)")
                )
            if "embedding_space_id" not in property_columns:
                await connection.execute(
                    text("alter table properties add column embedding_space_id varchar(64)")
                )
            pilot_property_columns = {
                "reference_code": "varchar(50)",
                "source_notes": "text",
                "address_text": "varchar(250)",
                "built_area_m2": "numeric(10,2)",
                "land_area_m2": "numeric(10,2)",
                "commercial_status": "varchar(20) not null default 'draft'",
            }
            for column, definition in pilot_property_columns.items():
                if column not in property_columns:
                    await connection.execute(
                        text(f"alter table properties add column {column} {definition}")
                    )
            command_target_columns = {
                "channel_account_id": "char(32)",
                "geographic_relevance": "varchar(160)",
                "property_tags": "json not null default '[]'",
                "is_demo": "boolean not null default 0",
            }
            for column, definition in command_target_columns.items():
                if column not in target_columns:
                    await connection.execute(
                        text(f"alter table publication_targets add column {column} {definition}")
                    )
            command_job_columns = {
                "action_required": "boolean not null default 0",
                "action_note": "varchar(300)",
            }
            for column, definition in command_job_columns.items():
                if column not in job_columns:
                    await connection.execute(
                        text(f"alter table publication_jobs add column {column} {definition}")
                    )
            command_publication_columns = {
                "channel_account_id": "char(32)",
                "external_publication_id": "varchar(180)",
            }
            for column, definition in command_publication_columns.items():
                if column not in publication_columns:
                    await connection.execute(
                        text(f"alter table publications add column {column} {definition}")
                    )
            legacy_matching_columns = {
                "requirements_fingerprint":
                    "varchar(64) not null default '00000000000000000000000000000000"
                    "00000000000000000000000000000000'",
                "embedding_space_id":
                    "varchar(64) not null default '00000000000000000000000000000000"
                    "00000000000000000000000000000000'",
                "invalidated_at": "datetime",
            }
            for column, definition in legacy_matching_columns.items():
                if column not in matching_columns:
                    await connection.execute(
                        text(f"alter table matching_runs add column {column} {definition}")
                    )
            if matching_columns and "invalidated_at" not in matching_columns:
                await connection.execute(
                    text(
                        "update matching_runs set invalidated_at = CURRENT_TIMESTAMP "
                        "where invalidated_at is null"
                    )
                )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
