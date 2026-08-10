from datetime import datetime
from uuid import uuid4

import psycopg
import pytest

from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres

EXPECTED_MIGRATIONS = (
    "20260809200000_initial_inventory_and_leads.sql",
    "20260810120000_structured_lead_extraction.sql",
)

EXPECTED_COLUMN_TYPES = {
    "leads": {
        "id": "uuid",
        "name": "text",
        "email": "text",
        "phone": "text",
        "original_request": "text",
        "idempotency_key": "uuid",
        "status": "text",
        "created_at": "timestamp with time zone",
        "updated_at": "timestamp with time zone",
    },
    "properties": {
        "id": "uuid",
        "title": "text",
        "description": "text",
        "operation_type": "text",
        "property_type": "text",
        "city": "text",
        "sector": "text",
        "monthly_price": "bigint",
        "sale_price": "bigint",
        "currency": "text",
        "bedrooms": "smallint",
        "bathrooms": "smallint",
        "parking_spaces": "smallint",
        "pet_policy": "text",
        "furnished": "boolean",
        "square_meters": "numeric(8,2)",
        "amenities": "text[]",
        "availability_status": "text",
        "source_text": "text",
        "embedding_text": "text",
        "embedding": "vector(1536)",
        "embedding_model": "text",
        "embedding_updated_at": "timestamp with time zone",
        "created_at": "timestamp with time zone",
        "updated_at": "timestamp with time zone",
    },
    "lead_requirements": {
        "id": "uuid",
        "lead_id": "uuid",
        "operation_type": "text",
        "property_types": "text[]",
        "locations": "text[]",
        "max_budget": "bigint",
        "currency": "text",
        "min_bedrooms": "smallint",
        "min_bathrooms": "smallint",
        "parking_required": "boolean",
        "pets_required": "boolean",
        "furnished_preference": "boolean",
        "soft_preferences": "text[]",
        "missing_information": "text[]",
        "extraction_confidence": "numeric(4,3)",
        "extraction_model": "text",
        "prompt_version": "text",
        "created_at": "timestamp with time zone",
        "updated_at": "timestamp with time zone",
    },
    "ai_runs": {
        "id": "uuid",
        "run_type": "text",
        "lead_id": "uuid",
        "property_id": "uuid",
        "provider": "text",
        "model": "text",
        "prompt_version": "text",
        "provider_request_id": "text",
        "latency_ms": "integer",
        "input_tokens": "integer",
        "output_tokens": "integer",
        "estimated_cost": "numeric(12,8)",
        "validation_passed": "boolean",
        "status": "text",
        "error_code": "text",
        "error_message": "text",
        "created_at": "timestamp with time zone",
    },
}

NULLABLE_COLUMNS = {
    "leads": {"name", "email", "phone"},
    "properties": {
        "sector",
        "monthly_price",
        "sale_price",
        "bedrooms",
        "bathrooms",
        "parking_spaces",
        "furnished",
        "square_meters",
        "embedding",
        "embedding_model",
        "embedding_updated_at",
    },
    "lead_requirements": {
        "max_budget",
        "currency",
        "min_bedrooms",
        "min_bathrooms",
        "parking_required",
        "pets_required",
        "furnished_preference",
    },
    "ai_runs": {
        "lead_id",
        "property_id",
        "prompt_version",
        "provider_request_id",
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "error_code",
        "error_message",
    },
}


def _expect_sqlstate(dsn: str, sql_text: str, expected: str) -> None:
    with psycopg.connect(dsn) as connection:
        with pytest.raises(psycopg.Error) as captured:
            connection.execute(sql_text)
    assert captured.value.sqlstate == expected


def test_migrations_apply_from_zero_in_authoritative_order(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    assert postgres_test_database.migration_names == EXPECTED_MIGRATIONS
    with psycopg.connect(postgres_test_database.dsn) as connection:
        version = connection.execute("show server_version").fetchone()
        extensions = dict(
            connection.execute(
                "select extname, extversion from pg_extension "
                "where extname in ('pgcrypto', 'vector')"
            ).fetchall()
        )

    assert version is not None and version[0].startswith("17.")
    assert extensions == {"pgcrypto": "1.3", "vector": "0.8.2"}


def test_columns_types_nullability_and_defaults_match_the_schema(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        rows = connection.execute(
            """
            select c.relname, a.attname, format_type(a.atttypid, a.atttypmod),
                   a.attnotnull, pg_get_expr(d.adbin, d.adrelid)
            from pg_attribute a
            join pg_class c on c.oid = a.attrelid
            join pg_namespace n on n.oid = c.relnamespace
            left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
            where n.nspname = 'public'
              and c.relname in ('leads', 'properties', 'lead_requirements', 'ai_runs')
              and a.attnum > 0 and not a.attisdropped
            order by c.relname, a.attnum
            """
        ).fetchall()

    actual_types: dict[str, dict[str, str]] = {}
    actual_not_null: dict[str, set[str]] = {}
    defaults: dict[tuple[str, str], str | None] = {}
    for table, column, data_type, not_null, default in rows:
        actual_types.setdefault(table, {})[column] = data_type
        if not_null:
            actual_not_null.setdefault(table, set()).add(column)
        defaults[(table, column)] = default

    assert actual_types == EXPECTED_COLUMN_TYPES
    for table, columns in EXPECTED_COLUMN_TYPES.items():
        assert actual_not_null[table] == set(columns) - NULLABLE_COLUMNS[table]

    for table in EXPECTED_COLUMN_TYPES:
        assert "gen_random_uuid" in str(defaults[(table, "id")])
    assert defaults[("leads", "status")] == "'new'::text"
    assert defaults[("properties", "amenities")] == "'{}'::text[]"
    assert defaults[("lead_requirements", "locations")] == "'{}'::text[]"
    assert defaults[("ai_runs", "latency_ms")] == "0"
    assert defaults[("ai_runs", "validation_passed")] == "false"
    assert defaults[("ai_runs", "status")] == "'running'::text"


def test_indexes_foreign_keys_unique_and_check_constraints_exist(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        index_rows = connection.execute(
            "select indexname, indexdef from pg_indexes "
            "where schemaname = 'public' order by indexname"
        ).fetchall()
        constraint_rows = connection.execute(
            """
            select c.relname, con.contype, pg_get_constraintdef(con.oid)
            from pg_constraint con
            join pg_class c on c.oid = con.conrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public'
            order by c.relname, con.contype, con.conname
            """
        ).fetchall()

    indexes = dict(index_rows)
    assert {
        "properties_inventory_idx",
        "properties_monthly_price_idx",
        "properties_sale_price_idx",
        "properties_bedrooms_idx",
        "properties_amenities_idx",
        "ai_runs_lead_created_idx",
    } <= indexes.keys()
    assert "USING gin (amenities)" in indexes["properties_amenities_idx"]
    assert "WHERE (monthly_price IS NOT NULL)" in indexes["properties_monthly_price_idx"]
    assert "created_at DESC" in indexes["ai_runs_lead_created_idx"]

    definitions = [(table, kind, definition) for table, kind, definition in constraint_rows]
    assert any(
        table == "leads" and kind == "u" and "UNIQUE (idempotency_key)" in definition
        for table, kind, definition in definitions
    )
    assert any(
        table == "lead_requirements" and kind == "u" and "UNIQUE (lead_id)" in definition
        for table, kind, definition in definitions
    )
    assert any(
        table == "lead_requirements"
        and kind == "f"
        and "REFERENCES leads(id) ON DELETE CASCADE" in definition
        for table, kind, definition in definitions
    )
    assert any(
        table == "ai_runs"
        and kind == "f"
        and "REFERENCES properties(id) ON DELETE SET NULL" in definition
        for table, kind, definition in definitions
    )
    assert sum(kind == "c" for _, kind, _ in definitions) >= 19


def test_constraints_reject_invalid_rows(postgres_test_database: PostgresTestDatabase) -> None:
    duplicate_key = uuid4()
    with psycopg.connect(postgres_test_database.dsn) as connection:
        connection.execute(
            "insert into public.leads (original_request, idempotency_key) values (%s, %s)",
            ("Solicitud sintética válida.", duplicate_key),
        )

    _expect_sqlstate(
        postgres_test_database.dsn,
        "insert into public.leads (original_request, idempotency_key) "
        f"values ('muy corto', '{uuid4()}')",
        "23514",
    )
    _expect_sqlstate(
        postgres_test_database.dsn,
        "insert into public.leads (original_request, idempotency_key) "
        f"values ('Otra solicitud sintética válida.', '{duplicate_key}')",
        "23505",
    )
    _expect_sqlstate(
        postgres_test_database.dsn,
        "insert into public.properties "
        "(title, description, operation_type, property_type, city, sale_price, "
        "source_text, embedding_text) values "
        "('Inválida', 'Solo prueba', 'rent', 'apartment', 'Viña del Mar', 100, "
        "'sintético', 'sintético')",
        "23514",
    )
    _expect_sqlstate(
        postgres_test_database.dsn,
        "insert into public.lead_requirements "
        "(lead_id, operation_type, extraction_confidence, extraction_model, prompt_version) "
        f"values ('{uuid4()}', 'rent', 0.5, 'fixture', 'v1')",
        "23503",
    )
    _expect_sqlstate(
        postgres_test_database.dsn,
        "insert into public.ai_runs (run_type, provider, model, latency_ms) "
        "values ('lead_extraction', 'fixture', 'fixture-v1', -1)",
        "23514",
    )


def test_update_triggers_and_timestamp_defaults_execute(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        row = connection.execute(
            "insert into public.leads (original_request, idempotency_key) "
            "values (%s, %s) returning id, created_at, updated_at",
            ("Solicitud sintética para validar timestamps.", uuid4()),
        ).fetchone()
        assert row is not None
        lead_id, created_at, previous_updated_at = row
        connection.commit()
        connection.execute("select pg_sleep(0.01)")
        current_updated_at = connection.execute(
            "update public.leads set status = 'qualified' where id = %s returning updated_at",
            (lead_id,),
        ).fetchone()
        triggers = connection.execute(
            """
            select c.relname, t.tgname
            from pg_trigger t
            join pg_class c on c.oid = t.tgrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and not t.tgisinternal
            order by c.relname
            """
        ).fetchall()
        function = connection.execute(
            "select pg_get_functiondef(p.oid), p.prosecdef from pg_proc p "
            "where p.oid = 'public.set_updated_at()'::regprocedure"
        ).fetchone()

    assert isinstance(created_at, datetime) and created_at.tzinfo is not None
    assert previous_updated_at == created_at
    assert current_updated_at is not None and current_updated_at[0] > previous_updated_at
    assert triggers == [
        ("lead_requirements", "lead_requirements_set_updated_at"),
        ("leads", "leads_set_updated_at"),
        ("properties", "properties_set_updated_at"),
    ]
    assert function is not None
    assert function[1] is False
    assert "SET search_path TO ''" in function[0]
