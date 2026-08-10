import asyncio
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import URL, make_url

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_DIRECTORY = REPOSITORY_ROOT / "supabase" / "migrations"
SEED_PATH = REPOSITORY_ROOT / "supabase" / "seed" / "properties.sql"
POSTGRES_URL_ENV = "ARRIENDATE_TEST_POSTGRES_URL"

if sys.platform == "win32":
    # psycopg async connections require selector-based sockets on Windows.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@dataclass(frozen=True, slots=True)
class PostgresTestDatabase:
    sqlalchemy_url: str
    dsn: str
    database_name: str
    migration_names: tuple[str, ...]


def _postgres_url() -> URL:
    raw_url = os.getenv(POSTGRES_URL_ENV)
    if not raw_url:
        pytest.fail(
            f"{POSTGRES_URL_ENV} is required for the PostgreSQL integration suite",
            pytrace=False,
        )
    parsed = make_url(raw_url)
    if parsed.get_backend_name() != "postgresql":
        pytest.fail(
            f"{POSTGRES_URL_ENV} must point to PostgreSQL, got {parsed.get_backend_name()}",
            pytrace=False,
        )
    return parsed


def _sync_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def _ensure_supabase_roles(admin_dsn: str) -> None:
    role_specs = {
        "anon": "nologin nobypassrls",
        "authenticated": "nologin nobypassrls",
        "service_role": "nologin bypassrls",
    }
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        for role, attributes in role_specs.items():
            exists = connection.execute(
                "select 1 from pg_roles where rolname = %s", (role,)
            ).fetchone()
            if exists is None:
                connection.execute(
                    sql.SQL("create role {} {}").format(
                        sql.Identifier(role), sql.SQL(attributes)
                    )
                )


def _apply_database_files(database_dsn: str) -> tuple[str, ...]:
    migrations = tuple(sorted(MIGRATIONS_DIRECTORY.glob("*.sql")))
    if not migrations:
        pytest.fail("No PostgreSQL migrations were found", pytrace=False)
    if len({path.name.split("_", 1)[0] for path in migrations}) != len(migrations):
        pytest.fail("PostgreSQL migration timestamps must be unique", pytrace=False)

    for migration in migrations:
        with psycopg.connect(database_dsn) as connection:
            connection.execute(migration.read_text(encoding="utf-8"))

    with psycopg.connect(database_dsn) as connection:
        connection.execute(SEED_PATH.read_text(encoding="utf-8"))
    return tuple(path.name for path in migrations)


@pytest.fixture(scope="session")
def postgres_test_database() -> Iterator[PostgresTestDatabase]:
    admin_url = _postgres_url()
    admin_dsn = _sync_dsn(admin_url)
    _ensure_supabase_roles(admin_dsn)
    database_name = f"arriendate_it_{uuid4().hex[:16]}"

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(
            sql.SQL("create database {} template template0 encoding 'UTF8'").format(
                sql.Identifier(database_name)
            )
        )

    database_url = admin_url.set(database=database_name)
    database_dsn = _sync_dsn(database_url)
    try:
        migration_names = _apply_database_files(database_dsn)
        yield PostgresTestDatabase(
            sqlalchemy_url=database_url.set(
                drivername="postgresql+psycopg"
            ).render_as_string(hide_password=False),
            dsn=database_dsn,
            database_name=database_name,
            migration_names=migration_names,
        )
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = %s and pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(
                sql.SQL("drop database if exists {}").format(sql.Identifier(database_name))
            )


@pytest.fixture(autouse=True)
def clean_application_rows(postgres_test_database: PostgresTestDatabase) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        connection.execute("truncate table public.leads cascade")
