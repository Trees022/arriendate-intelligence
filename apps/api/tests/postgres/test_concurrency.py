import asyncio
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from app.ai.contracts import StructuredGenerationRequest, StructuredGenerationResult
from app.ai.providers.fixture import StaticStructuredGenerator
from tests.factories import running_test_client, valid_requirements_json
from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres


class SynchronizedStructuredGenerator(StaticStructuredGenerator):
    def __init__(self, output_text: str, parties: int = 2) -> None:
        super().__init__(output_text)
        self.barrier = asyncio.Barrier(parties)

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        await self.barrier.wait()
        return await super().generate_structured(request)


async def test_simultaneous_identical_idempotent_lead_writes_return_one_row(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    key = str(uuid4())
    payload = {"original_request": "Solicitud sintética concurrente para un departamento."}
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        first, second = await asyncio.gather(
            client.post("/api/leads", json=payload, headers={"Idempotency-Key": key}),
            client.post("/api/leads", json=payload, headers={"Idempotency-Key": key}),
        )

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    with psycopg.connect(postgres_test_database.dsn) as connection:
        stored = connection.execute(
            "select count(*), count(distinct id) from public.leads where idempotency_key = %s",
            (key,),
        ).fetchone()
    assert stored == (1, 1)


async def test_simultaneous_conflicting_idempotent_writes_return_created_and_conflict(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    key = str(uuid4())
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        responses = await asyncio.gather(
            client.post(
                "/api/leads",
                json={"original_request": "Solicitud sintética A para departamento."},
                headers={"Idempotency-Key": key},
            ),
            client.post(
                "/api/leads",
                json={"original_request": "Solicitud sintética B para una casa familiar."},
                headers={"Idempotency-Key": key},
            ),
        )

    assert sorted(response.status_code for response in responses) == [201, 409]
    with psycopg.connect(postgres_test_database.dsn) as connection:
        count = connection.execute(
            "select count(*) from public.leads where idempotency_key = %s", (key,)
        ).fetchone()
    assert count == (1,)


async def test_simultaneous_extractions_use_atomic_requirement_upsert(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    generator = SynchronizedStructuredGenerator(valid_requirements_json())
    async with running_test_client(
        tmp_path,
        generator=generator,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        created = await client.post(
            "/api/leads",
            json={"original_request": "Solicitud sintética concurrente en Viña del Mar."},
            headers={"Idempotency-Key": str(uuid4())},
        )
        lead_id = created.json()["id"]
        first, second = await asyncio.gather(
            client.post(f"/api/leads/{lead_id}/extract"),
            client.post(f"/api/leads/{lead_id}/extract"),
        )

    assert first.status_code == second.status_code == 200
    with psycopg.connect(postgres_test_database.dsn) as connection:
        requirements = connection.execute(
            "select count(*), min(max_budget), max(max_budget) "
            "from public.lead_requirements where lead_id = %s",
            (lead_id,),
        ).fetchone()
        runs = connection.execute(
            "select count(*), bool_and(status = 'succeeded'), bool_and(validation_passed) "
            "from public.ai_runs where lead_id = %s",
            (lead_id,),
        ).fetchone()

    assert requirements == (1, 700_000, 700_000)
    assert runs == (2, True, True)


async def test_repeated_extraction_updates_one_requirement_and_records_each_attempt(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    async with running_test_client(
        tmp_path,
        generator=generator,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
    ) as client:
        created = await client.post(
            "/api/leads",
            json={"original_request": "Solicitud sintética repetida en Viña del Mar."},
            headers={"Idempotency-Key": str(uuid4())},
        )
        lead_id = created.json()["id"]
        first = await client.post(f"/api/leads/{lead_id}/extract")
        second = await client.post(f"/api/leads/{lead_id}/extract")

    assert first.status_code == second.status_code == 200
    with psycopg.connect(postgres_test_database.dsn) as connection:
        requirement = connection.execute(
            "select count(*), min(created_at), max(updated_at) "
            "from public.lead_requirements where lead_id = %s",
            (lead_id,),
        ).fetchone()
        run_count = connection.execute(
            "select count(*) from public.ai_runs where lead_id = %s", (lead_id,)
        ).fetchone()

    assert requirement is not None and requirement[0] == 1
    assert requirement[2] >= requirement[1]
    assert run_count == (2,)
