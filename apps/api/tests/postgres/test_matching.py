import asyncio
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from app.ai.providers.fixture import StaticStructuredGenerator
from app.db.session import Database
from app.embeddings.identity import embedding_space_id
from app.repositories.matching import MatchingRepository
from tests.factories import running_test_client, valid_requirements_json
from tests.postgres.conftest import PostgresTestDatabase

pytestmark = pytest.mark.postgres

FIRST_ID = "10000000-0000-4000-8000-000000000001"
FOURTH_ID = "10000000-0000-4000-8000-000000000004"
FIFTH_ID = "10000000-0000-4000-8000-000000000005"
EIGHTH_ID = "10000000-0000-4000-8000-000000000008"
TENTH_ID = "10000000-0000-4000-8000-000000000010"


def _basis(value: float) -> list[float]:
    return [value, *([0.0] * 1535)]


def _literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


class ControlledEmbeddingProvider:
    provider_name = "controlled"
    model = "controlled-pgvector-v1"
    dimension = 1536
    space_id = embedding_space_id(
        provider=provider_name, model=model, dimension=dimension
    )

    def __init__(self, *, tie_all_properties: bool = False) -> None:
        self.tie_all_properties = tie_all_properties

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for value in texts:
            if value.startswith("Preferencia:") or self.tie_all_properties:
                vectors.append(_basis(1.0))
            elif "Departamento Los Castaños" in value:
                vectors.append(_basis(1.0))
            elif "Departamento Recreo Alto" in value:
                vectors.append([0.8, 0.6, *([0.0] * 1534)])
            elif "Departamento Playa Ancha" in value:
                vectors.append(_basis(1.0))
            elif "Departamento Parque Curauma" in value:
                vectors.append([0.8, 0.6, *([0.0] * 1534)])
            elif "Departamento Centro Viña" in value:
                # This excluded property would win a semantic-only query.
                vectors.append(_basis(1.0))
            else:
                vectors.append(_basis(-1.0))
        return vectors


class BlockingEmbeddingProvider(ControlledEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.block_once = True

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.block_once:
            self.block_once = False
            self.started.set()
            await self.release.wait()
        return await super().embed(texts)


class CountingEmbeddingProvider(ControlledEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.provider_name = "cache-a"
        self.model = "cache-model-a"
        self.space_id = "a" * 64

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return await super().embed(texts)


async def _create_extracted_lead(client, output: str) -> str:
    created = await client.post(
        "/api/leads",
        json={"original_request": "Solicitud sintética suficientemente detallada."},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 201
    lead_id = created.json()["id"]
    extracted = await client.post(f"/api/leads/{lead_id}/extract")
    assert extracted.status_code == 200
    return lead_id


def test_pgvector_stores_reads_and_uses_cosine_with_nulls(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    with psycopg.connect(postgres_test_database.dsn) as connection:
        connection.execute(
            "update public.properties set embedding = null, embedding_model = null, "
            "embedding_updated_at = null where id in (%s, %s, %s)",
            (FIRST_ID, FOURTH_ID, FIFTH_ID),
        )
        connection.execute(
            "update public.properties set embedding = %s::vector where id = %s",
            (_literal(_basis(1.0)), FIRST_ID),
        )
        connection.execute(
            "update public.properties set embedding = %s::vector where id = %s",
            (_literal(_basis(-1.0)), FOURTH_ID),
        )
        stored = connection.execute(
            "select vector_dims(embedding), (embedding <=> %s::vector)::double precision "
            "from public.properties where id = %s",
            (_literal(_basis(1.0)), FIRST_ID),
        ).fetchone()
        ranked = connection.execute(
            "select id::text, (embedding <=> %s::vector)::double precision as distance "
            "from public.properties where id in (%s, %s, %s) and embedding is not null "
            "order by distance, id",
            (_literal(_basis(1.0)), FIRST_ID, FOURTH_ID, FIFTH_ID),
        ).fetchall()

    assert stored == (1536, 0.0)
    assert ranked == [(FIRST_ID, 0.0), (FOURTH_ID, 2.0)]


async def test_postgres_matching_combines_hard_gate_vector_order_and_top_k(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    output = valid_requirements_json(
        locations=["Valparaiso"],
        max_budget=700_000,
        min_bedrooms=2,
        min_bathrooms=None,
        parking_required=True,
        pets_required=True,
        soft_preferences=["luminoso"],
    )
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        generator=StaticStructuredGenerator(output),
        embedding_provider=ControlledEmbeddingProvider(),
    ) as client:
        lead_id = await _create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches?top_k=1")
        persisted = await client.get(f"/api/leads/{lead_id}/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_count"] == 2, body["exclusion_summary"]
    assert body["result_count"] == 1
    assert body["items"][0]["property"]["id"] == EIGHTH_ID
    assert body["items"][0]["semantic_score"] == 1.0
    assert FIFTH_ID not in {item["property"]["id"] for item in body["items"]}
    assert persisted.json()["items"] == body["items"]


async def test_postgres_pgvector_ties_are_deterministic(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    output = valid_requirements_json(
        locations=["Valparaiso"],
        max_budget=700_000,
        min_bedrooms=2,
        min_bathrooms=None,
        parking_required=None,
        pets_required=None,
        soft_preferences=["conectividad"],
    )
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        generator=StaticStructuredGenerator(output),
        embedding_provider=ControlledEmbeddingProvider(tie_all_properties=True),
    ) as client:
        lead_id = await _create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches?top_k=2")

    assert response.status_code == 200
    assert response.json()["candidate_count"] == 2, response.json()
    assert [item["property"]["id"] for item in response.json()["items"]] == [
        EIGHTH_ID,
        TENTH_ID,
    ]


async def test_postgres_reextraction_invalidates_previous_matching_snapshot(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        generator=generator,
        embedding_provider=ControlledEmbeddingProvider(),
    ) as client:
        lead_id = await _create_extracted_lead(client, generator.output_text)
        matched = await client.post(f"/api/leads/{lead_id}/matches")
        assert matched.status_code == 200
        assert matched.json()["result_count"] > 0

        generator.output_text = valid_requirements_json(max_budget=100_000)
        reextracted = await client.post(f"/api/leads/{lead_id}/extract")
        loaded = await client.get(f"/api/leads/{lead_id}/matches")

    assert reextracted.status_code == 200
    assert reextracted.json()["requirements"]["max_budget"] == 100_000
    assert loaded.status_code == 200
    assert loaded.json()["status"] == "not_run"
    with psycopg.connect(postgres_test_database.dsn) as connection:
        history = connection.execute(
            "select r.invalidated_at is not null, count(m.id) "
            "from public.matching_runs r left join public.property_matches m on m.run_id = r.id "
            "where r.lead_id = %s group by r.id, r.invalidated_at",
            (lead_id,),
        ).fetchone()
    assert history is not None
    assert history[0] is True
    assert history[1] > 0


async def test_requirements_change_during_matching_never_returns_stale_results(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    provider = BlockingEmbeddingProvider()
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        generator=generator,
        embedding_provider=provider,
    ) as client:
        lead_id = await _create_extracted_lead(client, generator.output_text)
        matching_task = asyncio.create_task(client.post(f"/api/leads/{lead_id}/matches"))
        await asyncio.wait_for(provider.started.wait(), timeout=2)

        generator.output_text = valid_requirements_json(max_budget=100_000)
        reextracted = await client.post(f"/api/leads/{lead_id}/extract")
        assert reextracted.status_code == 200
        provider.release.set()
        stale_response = await matching_task
        latest = await client.get(f"/api/leads/{lead_id}/matches")

    assert stale_response.status_code == 409
    assert latest.json()["status"] == "not_run"
    with psycopg.connect(postgres_test_database.dsn) as connection:
        history = connection.execute(
            "select r.status, r.invalidated_at is not null, count(m.id) "
            "from public.matching_runs r left join public.property_matches m on m.run_id = r.id "
            "where r.lead_id = %s group by r.id, r.status, r.invalidated_at",
            (lead_id,),
        ).fetchone()
    assert history is not None
    assert history[0:2] == ("succeeded", True)
    assert history[2] > 0


async def test_concurrent_same_lead_requests_are_consistent_duplicate_work_only(
    tmp_path: Path,
    postgres_test_database: PostgresTestDatabase,
) -> None:
    output = valid_requirements_json(soft_preferences=[], furnished_preference=None)
    async with running_test_client(
        tmp_path,
        database_url=postgres_test_database.sqlalchemy_url,
        seed_demo_data=False,
        generator=StaticStructuredGenerator(output),
    ) as client:
        lead_id = await _create_extracted_lead(client, output)
        first, second = await asyncio.gather(
            client.post(f"/api/leads/{lead_id}/matches"),
            client.post(f"/api/leads/{lead_id}/matches"),
        )
        latest = await client.get(f"/api/leads/{lead_id}/matches")

    assert first.status_code == second.status_code == 200
    assert first.json()["items"] == second.json()["items"] == latest.json()["items"]
    with psycopg.connect(postgres_test_database.dsn) as connection:
        current_runs = connection.execute(
            "select count(*) from public.matching_runs "
            "where lead_id = %s and invalidated_at is null and status = 'succeeded'",
            (lead_id,),
        ).fetchone()
    assert current_runs == (2,)


async def test_property_embedding_cache_is_scoped_to_provider_model_space_and_text(
    postgres_test_database: PostgresTestDatabase,
) -> None:
    database = Database(postgres_test_database.sqlalchemy_url)
    provider = CountingEmbeddingProvider()
    try:
        async with database.session() as session:
            repository = MatchingRepository(session)
            properties = (await repository.list_properties())[:1]
            original_description = properties[0].description
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 1
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 1

            provider.provider_name = "cache-b"
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 2
            provider.model = "cache-model-b"
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 3
            provider.space_id = "b" * 64
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 4
            properties[0].description += " Cambio canónico."
            await repository.ensure_property_embeddings(properties, provider)
            assert provider.calls == 5
            properties[0].description = original_description
            properties[0].embedding_text = original_description
            await session.commit()
    finally:
        await database.dispose()
