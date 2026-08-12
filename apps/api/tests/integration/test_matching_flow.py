import sqlite3
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

import pytest

from app.ai.providers.fixture import StaticStructuredGenerator
from app.embeddings.errors import EmbeddingError
from app.embeddings.providers.disabled import DisabledEmbeddingProvider
from app.repositories.matching import MatchingRepository
from tests.factories import running_test_client, valid_requirements_json


async def create_extracted_lead(client, output: str) -> str:
    created = await client.post(
        "/api/leads",
        json={"original_request": "Solicitud sintética suficientemente detallada."},
        headers={"Idempotency-Key": str(uuid4())},
    )
    lead_id = created.json()["id"]
    extracted = await client.post(f"/api/leads/{lead_id}/extract")
    assert extracted.status_code == 200
    return lead_id


async def test_matching_filters_hard_constraints_ranks_and_persists(tmp_path: Path) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    async with running_test_client(tmp_path, generator=generator) as client:
        lead_id = await create_extracted_lead(client, valid_requirements_json())
        response = await client.post(f"/api/leads/{lead_id}/matches?top_k=3")
        loaded = await client.get(f"/api/leads/{lead_id}/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["candidate_count"] == 2
    assert body["result_count"] == 2
    assert [item["property"]["id"] for item in body["items"]] == [
        item["property"]["id"] for item in loaded.json()["items"]
    ]
    assert all(
        check["passed"]
        for item in body["items"]
        for check in item["hard_constraint_matches"]
    )
    assert all(0 <= item["semantic_score"] <= 1 for item in body["items"])


async def test_impossible_constraints_return_zero_without_provider(
    tmp_path: Path,
) -> None:
    output = valid_requirements_json(
        max_budget=100_000,
        min_bedrooms=10,
        soft_preferences=["luminoso"],
    )
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=DisabledEmbeddingProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_count"] == 0
    assert body["items"] == []
    assert {item["constraint"] for item in body["exclusion_summary"]} >= {
        "max_budget",
        "min_bedrooms",
    }


async def test_matching_without_requirements_is_conflict(tmp_path: Path) -> None:
    async with running_test_client(tmp_path) as client:
        created = await client.post(
            "/api/leads",
            json={"original_request": "Solicitud sintética sin extracción todavía."},
            headers={"Idempotency-Key": str(uuid4())},
        )
        response = await client.post(f"/api/leads/{created.json()['id']}/matches")
    assert response.status_code == 409


async def test_provider_failure_is_observed_and_sanitized(tmp_path: Path) -> None:
    output = valid_requirements_json(soft_preferences=["luminoso"])
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=DisabledEmbeddingProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches")
    assert response.status_code == 503
    assert response.json()["type"].endswith("/embedding_provider_unavailable")
    with sqlite3.connect(tmp_path / "test.db") as connection:
        observed = connection.execute(
            "select status, total_properties, candidate_count, error_code, error_message "
            "from matching_runs order by created_at desc limit 1"
        ).fetchone()
    assert observed is not None
    assert observed[:4] == ("failed", 18, 2, "embedding_provider_not_configured")
    assert "key" not in observed[4].casefold()


async def test_no_soft_preferences_need_no_provider_and_have_no_score(tmp_path: Path) -> None:
    output = valid_requirements_json(soft_preferences=[], furnished_preference=None)
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=DisabledEmbeddingProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches?top_k=1")
    assert response.status_code == 200
    assert response.json()["items"][0]["semantic_score"] is None


@pytest.mark.parametrize("top_k", ["0", "-1", "11", "invalid"])
async def test_top_k_is_bounded_and_typed(tmp_path: Path, top_k: str) -> None:
    async with running_test_client(tmp_path) as client:
        response = await client.post(f"/api/leads/{uuid4()}/matches?top_k={top_k}")
    assert response.status_code == 422


async def test_matching_missing_lead_is_not_found(tmp_path: Path) -> None:
    async with running_test_client(tmp_path) as client:
        response = await client.post(f"/api/leads/{uuid4()}/matches")
    assert response.status_code == 404


async def test_default_top_k_is_three(tmp_path: Path) -> None:
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(valid_requirements_json()),
    ) as client:
        lead_id = await create_extracted_lead(client, valid_requirements_json())
        response = await client.post(f"/api/leads/{lead_id}/matches")
    assert response.status_code == 200
    assert response.json()["requested_top_k"] == 3


async def test_budget_without_currency_or_operation_is_rejected_for_matching(
    tmp_path: Path,
) -> None:
    for output in (
        valid_requirements_json(currency=None, missing_information=["currency"]),
        valid_requirements_json(
            operation_type="unknown", missing_information=["operation_type"]
        ),
    ):
        async with running_test_client(
            tmp_path,
            generator=StaticStructuredGenerator(output),
        ) as client:
            lead_id = await create_extracted_lead(client, output)
            response = await client.post(f"/api/leads/{lead_id}/matches")
        assert response.status_code == 409


class UnexpectedProvider:
    provider_name = "unexpected"
    model = "unexpected-v1"
    dimension = 1536
    space_id = "1" * 64

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise RuntimeError("upstream-secret-must-not-persist")


class ZeroVectorProvider:
    provider_name = "zero"
    model = "zero-v1"
    dimension = 1536
    space_id = "2" * 64

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]


class ZeroQueryProvider(ZeroVectorProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls == 1:
            return [[1.0, *([0.0] * (self.dimension - 1))] for _ in texts]
        return await super().embed(texts)


class ExpectedErrorProvider(ZeroVectorProvider):
    def __init__(self, *, timeout: bool) -> None:
        self.timeout = timeout

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingError(
            "embedding_timeout" if self.timeout else "invalid_embedding_response",
            "El proveedor devolvió una respuesta inválida",
            timeout=self.timeout,
        )


async def test_unexpected_exception_marks_run_failed_and_preserves_original(
    tmp_path: Path,
) -> None:
    output = valid_requirements_json(soft_preferences=["luminoso"])
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=UnexpectedProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        with pytest.raises(RuntimeError, match="upstream-secret"):
            await client.post(f"/api/leads/{lead_id}/matches")
    with sqlite3.connect(tmp_path / "test.db") as connection:
        observed = connection.execute(
            "select status, result_count, error_code, error_message "
            "from matching_runs order by created_at desc limit 1"
        ).fetchone()
    assert observed == (
        "failed",
        0,
        "matching_internal_error",
        "El matching no pudo completarse por un error interno",
    )


async def test_failure_persistence_failure_does_not_replace_original_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken_fail(*args, **kwargs) -> None:
        raise RuntimeError("secondary persistence failure")

    monkeypatch.setattr(MatchingRepository, "fail_run", broken_fail)
    output = valid_requirements_json(soft_preferences=["luminoso"])
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=UnexpectedProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        with pytest.raises(RuntimeError, match="upstream-secret"):
            await client.post(f"/api/leads/{lead_id}/matches")


async def test_zero_vector_failure_is_sanitized_and_persisted(tmp_path: Path) -> None:
    output = valid_requirements_json(soft_preferences=["luminoso"])
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=ZeroVectorProvider(),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches")
    assert response.status_code == 503
    with sqlite3.connect(tmp_path / "test.db") as connection:
        observed = connection.execute(
            "select status, result_count, error_code from matching_runs "
            "order by created_at desc limit 1"
        ).fetchone()
    assert observed == ("failed", 0, "invalid_embedding_zero_vector")


async def test_zero_query_vector_is_rejected_after_valid_property_vectors(
    tmp_path: Path,
) -> None:
    output = valid_requirements_json(soft_preferences=["luminoso"])
    provider = ZeroQueryProvider()
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=provider,
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches")
    assert response.status_code == 503
    assert provider.calls == 2


@pytest.mark.parametrize(("is_timeout", "status"), [(True, 504), (False, 503)])
async def test_expected_provider_failure_status_codes_are_sanitized(
    tmp_path: Path, is_timeout: bool, status: int
) -> None:
    output = valid_requirements_json(soft_preferences=["luminoso"])
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(output),
        embedding_provider=ExpectedErrorProvider(timeout=is_timeout),
    ) as client:
        lead_id = await create_extracted_lead(client, output)
        response = await client.post(f"/api/leads/{lead_id}/matches")
    assert response.status_code == status
    assert "traceback" not in response.text.casefold()


async def test_reextraction_invalidates_matches_from_previous_requirements(
    tmp_path: Path,
) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    async with running_test_client(tmp_path, generator=generator) as client:
        lead_id = await create_extracted_lead(client, generator.output_text)
        matched = await client.post(f"/api/leads/{lead_id}/matches")
        assert matched.status_code == 200
        assert matched.json()["result_count"] > 0

        generator.output_text = valid_requirements_json(max_budget=100_000)
        reextracted = await client.post(f"/api/leads/{lead_id}/extract")
        assert reextracted.status_code == 200
        assert reextracted.json()["requirements"]["max_budget"] == 100_000

        loaded = await client.get(f"/api/leads/{lead_id}/matches")
        assert loaded.status_code == 200
        assert loaded.json()["status"] == "not_run"
        assert loaded.json()["items"] == []

        rematched = await client.post(f"/api/leads/{lead_id}/matches")
        assert rematched.status_code == 200
        assert rematched.json()["run_id"] != matched.json()["run_id"]

    with sqlite3.connect(tmp_path / "test.db") as connection:
        history = connection.execute(
            "select r.invalidated_at is not null, count(m.id) "
            "from matching_runs r left join property_matches m on m.run_id = r.id "
            "where r.lead_id = ? group by r.id, r.invalidated_at order by r.invalidated_at desc",
            (lead_id.replace("-", ""),),
        ).fetchall()
    assert len(history) == 2
    assert history[0][0] == 1 and history[0][1] > 0
    assert history[1][0] == 0
