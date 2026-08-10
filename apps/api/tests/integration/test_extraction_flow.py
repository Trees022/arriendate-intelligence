import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from httpx import AsyncClient

from app.ai.errors import ProviderError, ProviderNotConfiguredError
from app.ai.providers.fixture import StaticStructuredGenerator
from tests.factories import running_test_client, valid_requirements_json


async def create_lead(
    client: AsyncClient, request: str = "Busco un departamento en Viña del Mar."
) -> str:
    response = await client.post(
        "/api/leads",
        json={"original_request": request},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def test_successful_extraction_persists_requirements_and_observability(
    tmp_path: Path,
) -> None:
    generator = StaticStructuredGenerator(valid_requirements_json())
    async with running_test_client(
        tmp_path,
        generator=generator,
        ai_input_cost_per_million=Decimal("1.00"),
        ai_output_cost_per_million=Decimal("6.00"),
    ) as client:
        lead_id = await create_lead(client)
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 200
        body = extracted.json()
        assert body["lead_status"] == "qualified"
        assert body["requirements"]["max_budget"] == 700_000
        assert body["requirements"]["extraction_model"] == generator.model
        assert body["requirements"]["prompt_version"] == "lead-extraction-v1.0.0"
        assert body["ai_run"]["status"] == "succeeded"
        assert body["ai_run"]["validation_passed"] is True
        assert body["ai_run"]["input_tokens"] == 120
        assert body["ai_run"]["output_tokens"] == 80
        assert body["ai_run"]["estimated_cost"] == 0.0006
        assert len(generator.calls) == 1
        assert "original_request" in generator.calls[0].messages[1].content

        detail = (await client.get(f"/api/leads/{lead_id}")).json()
        assert detail["requirements"]["locations"] == ["Viña del Mar"]
        assert len(detail["ai_runs"]) == 1
        assert detail["ai_runs"][0]["provider_request_id"] == "fixture-request-1"


async def test_missing_information_changes_status_without_inventing_values(tmp_path: Path) -> None:
    output = valid_requirements_json(
        max_budget=None,
        currency=None,
        missing_information=["budget"],
        confidence=0.72,
    )
    async with running_test_client(tmp_path, generator=StaticStructuredGenerator(output)) as client:
        lead_id = await create_lead(client, "Busco departamento en Viña, no tengo presupuesto aún.")
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 200
        assert extracted.json()["lead_status"] == "needs_information"
        assert extracted.json()["requirements"]["max_budget"] is None
        assert extracted.json()["requirements"]["missing_information"] == ["budget"]


async def test_malformed_provider_output_is_rejected_and_observed(tmp_path: Path) -> None:
    malformed = '{"operation_type":"rent"'
    async with running_test_client(
        tmp_path, generator=StaticStructuredGenerator(malformed)
    ) as client:
        lead_id = await create_lead(client)
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 502
        assert extracted.json()["type"].endswith("/invalid_ai_output")
        detail = (await client.get(f"/api/leads/{lead_id}")).json()
        assert detail["requirements"] is None
        assert detail["status"] == "new"
        assert detail["ai_runs"][0]["status"] == "failed"
        assert detail["ai_runs"][0]["error_code"] == "invalid_model_output"
        assert malformed not in json.dumps(detail["ai_runs"][0])


async def test_incomplete_provider_output_is_rejected_and_observed(tmp_path: Path) -> None:
    incomplete = json.loads(valid_requirements_json())
    incomplete.pop("confidence")
    async with running_test_client(
        tmp_path,
        generator=StaticStructuredGenerator(json.dumps(incomplete)),
    ) as client:
        lead_id = await create_lead(client)
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 502
        detail = (await client.get(f"/api/leads/{lead_id}")).json()
        assert detail["requirements"] is None
        assert detail["ai_runs"][0]["validation_passed"] is False
        assert detail["ai_runs"][0]["error_message"] == (
            "La salida del proveedor no cumplió el esquema validado"
        )


async def test_unconfigured_provider_returns_useful_error_and_run(tmp_path: Path) -> None:
    generator = StaticStructuredGenerator(
        "",
        error=ProviderNotConfiguredError(),
    )
    async with running_test_client(tmp_path, generator=generator) as client:
        lead_id = await create_lead(client)
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 503
        assert "no está configurado" in extracted.json()["detail"]
        detail = (await client.get(f"/api/leads/{lead_id}")).json()
        assert detail["ai_runs"][0]["error_code"] == "provider_not_configured"


async def test_incomplete_provider_execution_returns_bad_gateway_and_is_observed(
    tmp_path: Path,
) -> None:
    generator = StaticStructuredGenerator(
        "",
        error=ProviderError(
            code="provider_incomplete",
            message="El proveedor no completó la extracción",
        ),
    )
    async with running_test_client(tmp_path, generator=generator) as client:
        lead_id = await create_lead(client)
        extracted = await client.post(f"/api/leads/{lead_id}/extract")

        assert extracted.status_code == 502
        assert extracted.json()["type"].endswith("/ai_provider_response_error")
        detail = (await client.get(f"/api/leads/{lead_id}")).json()
        assert detail["requirements"] is None
        assert detail["ai_runs"][0]["error_code"] == "provider_incomplete"
