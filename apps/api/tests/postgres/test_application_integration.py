import asyncio
import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from httpx import AsyncClient

from app.ai.providers.fixture import StaticStructuredGenerator
from app.repositories.extractions import ExtractionRepository
from tests.factories import running_test_client, valid_requirements_json
from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres


async def _create_lead(
    client: AsyncClient,
    *,
    request: str = "Busco un departamento sintético en Viña del Mar.",
    idempotency_key: str | None = None,
) -> dict[str, object]:
    response = await client.post(
        "/api/leads",
        json={"name": "Persona Demo", "original_request": request},
        headers={"Idempotency-Key": idempotency_key or str(uuid4())},
    )
    assert response.status_code == 201
    return dict(response.json())


async def test_lead_creation_original_text_idempotency_and_detail_use_postgresql(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    original = "  Busco departamento en Concón.\nDebe admitir mascotas y tener estacionamiento.  "
    key = str(uuid4())
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        first = await _create_lead(client, request=original, idempotency_key=key)
        second = await _create_lead(client, request=original, idempotency_key=key)
        detail = await client.get(f"/api/leads/{first['id']}")

    assert second["id"] == first["id"]
    assert detail.status_code == 200
    assert detail.json()["original_request"] == original
    assert detail.json()["requirements"] is None
    assert detail.json()["ai_runs"] == []
    with psycopg.connect(postgres_test_database.dsn) as connection:
        stored = connection.execute(
            "select original_request, status, idempotency_key, created_at, updated_at "
            "from public.leads where id = %s",
            (first["id"],),
        ).fetchone()
    assert stored is not None
    assert stored[0:2] == (original, "new")
    assert str(stored[2]) == key
    assert stored[3].tzinfo is not None and stored[4].tzinfo is not None


async def test_successful_extraction_persists_arrays_numeric_metadata_and_status_atomically(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    output = valid_requirements_json(
        property_types=["apartment", "loft"],
        locations=["Viña del Mar", "Concón"],
        soft_preferences=["sector tranquilo", "balcón"],
    )
    generator = StaticStructuredGenerator(output)
    async with running_test_client(
        tmp_path,
        generator=generator,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        ai_input_cost_per_million=Decimal("1.00"),
        ai_output_cost_per_million=Decimal("6.00"),
    ) as client:
        lead = await _create_lead(client)
        extracted = await client.post(f"/api/leads/{lead['id']}/extract")
        detail = await client.get(f"/api/leads/{lead['id']}")

    assert extracted.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["requirements"]["locations"] == ["Viña del Mar", "Concón"]
    assert detail.json()["ai_runs"][0]["status"] == "succeeded"
    with psycopg.connect(postgres_test_database.dsn) as connection:
        requirement = connection.execute(
            """
            select property_types, locations, soft_preferences, missing_information,
                   extraction_confidence, extraction_model, prompt_version
            from public.lead_requirements where lead_id = %s
            """,
            (lead["id"],),
        ).fetchone()
        run = connection.execute(
            """
            select status, validation_passed, provider_request_id, input_tokens,
                   output_tokens, estimated_cost
            from public.ai_runs where lead_id = %s
            """,
            (lead["id"],),
        ).fetchone()
        status = connection.execute(
            "select status from public.leads where id = %s", (lead["id"],)
        ).fetchone()

    assert requirement == (
        ["apartment", "loft"],
        ["Viña del Mar", "Concón"],
        ["sector tranquilo", "balcón"],
        [],
        Decimal("0.960"),
        "fixture-structured-v1",
        "lead-extraction-v1.0.0",
    )
    assert run == ("succeeded", True, "fixture-request-1", 120, 80, Decimal("0.00060000"))
    assert status == ("qualified",)


@pytest.mark.parametrize(
    "provider_output",
    [
        '{"operation_type":"rent"',
        json.dumps(
            {
                "operation_type": "rent",
                "property_types": ["apartment"],
                "locations": ["Viña del Mar"],
                "max_budget": 700_000,
                "currency": "CLP",
                "min_bedrooms": 2,
                "min_bathrooms": None,
                "parking_required": True,
                "pets_required": True,
                "furnished_preference": None,
                "soft_preferences": [],
                "missing_information": [],
            }
        ),
    ],
)
async def test_malformed_and_incomplete_provider_outputs_store_only_sanitized_failure(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
    provider_output: str,
) -> None:
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(provider_output),
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        lead = await _create_lead(client)
        response = await client.post(f"/api/leads/{lead['id']}/extract")

    assert response.status_code == 502
    with psycopg.connect(postgres_test_database.dsn) as connection:
        requirement_count = connection.execute(
            "select count(*) from public.lead_requirements where lead_id = %s", (lead["id"],)
        ).fetchone()
        state = connection.execute(
            """
            select l.status, r.status, r.validation_passed, r.error_code, r.error_message
            from public.leads l join public.ai_runs r on r.lead_id = l.id
            where l.id = %s
            """,
            (lead["id"],),
        ).fetchone()

    assert requirement_count == (0,)
    assert state == (
        "new",
        "failed",
        False,
        "invalid_model_output",
        "La salida del proveedor no cumplió el esquema validado",
    )
    assert provider_output not in str(state)


async def test_persistence_failure_rolls_back_requirements_and_lead_status_but_keeps_failed_run(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_before_success_commit(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(0)
        raise RuntimeError("synthetic persistence failure")

    monkeypatch.setattr(ExtractionRepository, "mark_run_succeeded", fail_before_success_commit)
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(valid_requirements_json()),
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        lead = await _create_lead(client)
        with pytest.raises(RuntimeError, match="synthetic persistence failure"):
            await client.post(f"/api/leads/{lead['id']}/extract")

    with psycopg.connect(postgres_test_database.dsn) as connection:
        requirement_count = connection.execute(
            "select count(*) from public.lead_requirements where lead_id = %s", (lead["id"],)
        ).fetchone()
        state = connection.execute(
            """
            select l.status, r.status, r.validation_passed, r.error_code
            from public.leads l join public.ai_runs r on r.lead_id = l.id
            where l.id = %s
            """,
            (lead["id"],),
        ).fetchone()

    assert requirement_count == (0,)
    assert state == ("new", "failed", False, "persistence_error")
