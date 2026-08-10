import json
from typing import Any

import httpx
import pytest

from app.ai.contracts import PromptMessage, StructuredGenerationRequest
from app.ai.errors import ProviderError
from app.ai.providers.openai_compatible import OpenAICompatibleStructuredGenerator
from app.ai.schemas import LeadRequirements
from tests.factories import valid_requirements_json


def request_contract() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        messages=(
            PromptMessage(role="developer", content="Extract only grounded data."),
            PromptMessage(role="user", content='{"original_request":"Busco departamento"}'),
        ),
        schema_name="lead_requirements",
        schema=LeadRequirements.model_json_schema(),
    )


def response_body(output_text: str) -> dict[str, Any]:
    return {
        "id": "resp_test_123",
        "model": "gpt-5.6-luna",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": output_text}],
            }
        ],
        "usage": {"input_tokens": 111, "output_tokens": 57},
    }


async def test_responses_api_payload_uses_strict_json_schema_and_parses_usage() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=response_body(valid_requirements_json()))

    provider = OpenAICompatibleStructuredGenerator(
        base_url="https://provider.test/v1",
        api_key="test-secret-not-real",
        model="gpt-5.6-luna",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.generate_structured(request_contract())

    body = captured["body"]
    assert captured["path"] == "/v1/responses"
    assert captured["authorization"] == "Bearer test-secret-not-real"
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
    assert result.provider_request_id == "resp_test_123"
    assert result.input_tokens == 111
    assert result.output_tokens == 57


async def test_transient_failures_retry_only_to_the_configured_bound() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(500)
        return httpx.Response(200, json=response_body(valid_requirements_json()))

    provider = OpenAICompatibleStructuredGenerator(
        base_url="https://provider.test/v1",
        api_key="test-secret-not-real",
        model="gpt-5.6-luna",
        max_retries=2,
        retry_delay_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    await provider.generate_structured(request_contract())
    assert attempts == 3


async def test_non_retryable_provider_error_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "sensitive provider body"}})

    provider = OpenAICompatibleStructuredGenerator(
        base_url="https://provider.test/v1",
        api_key="test-secret-not-real",
        model="gpt-5.6-luna",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderError) as captured:
        await provider.generate_structured(request_contract())

    assert captured.value.code == "provider_http_400"
    assert "sensitive provider body" not in captured.value.safe_message


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        ({"id": "resp_incomplete", "status": "incomplete", "output": []}, "provider_incomplete"),
        ({"id": "resp_empty", "status": "completed", "output": []}, "missing_provider_output"),
        (
            {
                "id": "resp_refusal",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "not available"}],
                    }
                ],
            },
            "provider_refusal",
        ),
    ],
)
async def test_incomplete_or_missing_provider_output_is_rejected(
    body: dict[str, Any], expected_code: str
) -> None:
    provider = OpenAICompatibleStructuredGenerator(
        base_url="https://provider.test/v1",
        api_key="test-secret-not-real",
        model="gpt-5.6-luna",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )

    with pytest.raises(ProviderError) as captured:
        await provider.generate_structured(request_contract())

    assert captured.value.code == expected_code


async def test_non_json_provider_envelope_is_rejected_without_leaking_body() -> None:
    provider = OpenAICompatibleStructuredGenerator(
        base_url="https://provider.test/v1",
        api_key="test-secret-not-real",
        model="gpt-5.6-luna",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="private upstream diagnostic")
        ),
    )

    with pytest.raises(ProviderError) as captured:
        await provider.generate_structured(request_contract())

    assert captured.value.code == "invalid_provider_response"
    assert "private upstream diagnostic" not in captured.value.safe_message
