from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres

APPLICATION_TABLES = (
    "leads",
    "properties",
    "lead_requirements",
    "ai_runs",
    "matching_runs",
    "property_matches",
)
DIRECT_DATA_API_ROLES = ("anon", "authenticated")


def test_rls_is_enabled_without_permissive_policies(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        rls_rows = connection.execute(
            """
            select c.relname, c.relrowsecurity, c.relforcerowsecurity
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relname = any(%s)
            order by c.relname
            """,
            (list(APPLICATION_TABLES),),
        ).fetchall()
        policies = connection.execute(
            "select tablename, policyname from pg_policies "
            "where schemaname = 'public' and tablename = any(%s)",
            (list(APPLICATION_TABLES),),
        ).fetchall()

    assert rls_rows == [
        ("ai_runs", True, False),
        ("lead_requirements", True, False),
        ("leads", True, False),
        ("matching_runs", True, False),
        ("properties", True, False),
        ("property_matches", True, False),
    ]
    assert policies == []


@pytest.mark.parametrize("role", DIRECT_DATA_API_ROLES)
@pytest.mark.parametrize("table", APPLICATION_TABLES)
def test_anon_and_authenticated_have_no_direct_table_privileges(
    postgres_test_database: PostgresTestDatabase,
    role: str,
    table: str,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        privileges = connection.execute(
            "select has_table_privilege(%s, %s, %s)",
            (role, f"public.{table}", "SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER"),
        ).fetchone()
        connection.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            query = sql.SQL("select * from public.{} limit 1").format(
                sql.Identifier(table)
            )
            connection.execute(query)

    assert privileges == (False,)


def test_rls_remains_deny_by_default_even_if_a_read_grant_is_added(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        connection.execute("grant select on public.properties to authenticated")
        connection.execute("set local role authenticated")
        visible_count = connection.execute("select count(*) from public.properties").fetchone()
        connection.execute("reset role")
        connection.rollback()

    assert visible_count == (0,)


def test_rls_blocks_unprivileged_insert_even_with_table_grant(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        connection.execute("grant insert on public.leads to anon")
        connection.execute("set local role anon")
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as captured:
            connection.execute(
                "insert into public.leads (original_request, idempotency_key) values (%s, %s)",
                ("Solicitud sintética que RLS debe rechazar.", uuid4()),
            )

    assert captured.value.sqlstate == "42501"


def test_privileged_server_roles_bypass_rls_only_with_object_privileges(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        service_role = connection.execute(
            "select rolbypassrls from pg_roles where rolname = 'service_role'"
        ).fetchone()
        owner_visible_count = connection.execute(
            "select count(*) from public.properties"
        ).fetchone()
        service_has_grant = connection.execute(
            "select has_table_privilege('service_role', 'public.properties', 'SELECT')"
        ).fetchone()

        connection.execute("grant select on public.properties to service_role")
        connection.execute("set local role service_role")
        service_visible_count = connection.execute(
            "select count(*) from public.properties"
        ).fetchone()
        connection.execute("reset role")
        connection.rollback()

    assert service_role == (True,)
    assert owner_visible_count == (18,)
    assert service_has_grant == (False,)
    assert service_visible_count == (18,)


def test_sensitive_tables_are_not_exposed_through_role_grants(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        grants = connection.execute(
            """
            select grantee, table_name, privilege_type
            from information_schema.role_table_grants
            where table_schema = 'public'
              and table_name in (
                'lead_requirements', 'ai_runs', 'matching_runs', 'property_matches'
              )
              and grantee in ('anon', 'authenticated')
            """
        ).fetchall()

    assert grants == []
