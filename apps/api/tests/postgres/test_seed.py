from pathlib import Path

import psycopg
import pytest

from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SEED_SQL = (REPOSITORY_ROOT / "supabase" / "seed" / "properties.sql").read_text(
    encoding="utf-8"
)


def test_all_synthetic_properties_load_with_postgresql_types(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        summary = connection.execute(
            """
            select count(*), count(distinct id), count(*) filter (where embedding is null),
                   bool_and(source_text = description),
                   bool_and(cardinality(amenities) >= 0),
                   bool_and(
                     (operation_type = 'rent' and monthly_price is not null and sale_price is null)
                     or (
                       operation_type = 'buy' and sale_price is not null
                       and monthly_price is null
                     )
                   )
            from public.properties
            """
        ).fetchone()
        accented = connection.execute(
            "select title, city, amenities from public.properties "
            "where id = '10000000-0000-4000-8000-000000000001'"
        ).fetchone()
        incomplete = connection.execute(
            "select bedrooms, parking_spaces, furnished, square_meters, amenities "
            "from public.properties "
            "where id = '10000000-0000-4000-8000-000000000017'"
        ).fetchone()
        table_comment = connection.execute(
            "select obj_description('public.properties'::regclass, 'pg_class')"
        ).fetchone()

    assert summary == (18, 18, 18, True, True, True)
    assert accented == (
        "Departamento Los Castaños",
        "Viña del Mar",
        ["balcón", "conserjería", "bodega"],
    )
    assert incomplete == (None, None, None, None, [])
    assert table_comment == (
        "Synthetic demo inventory. Real client data is prohibited in v0.1.",
    )


def test_seed_can_be_reapplied_without_duplicates(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        before = connection.execute(
            "select id, title from public.properties order by id"
        ).fetchall()
        connection.execute(SEED_SQL)
        after = connection.execute(
            "select id, title from public.properties order by id"
        ).fetchall()

    assert len(before) == 18
    assert after == before


def test_seed_file_contains_only_deterministic_inventory_without_contact_data() -> None:
    normalized = SEED_SQL.casefold()
    assert "10000000-0000-4000-8000-000000000001" in normalized
    assert "10000000-0000-4000-8000-000000000018" in normalized
    assert '"email"' not in normalized
    assert '"phone"' not in normalized
    assert "@" not in normalized
