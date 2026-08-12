import json

import httpx
import pytest
from pydantic import ValidationError

from app.core.settings import Settings
from app.embeddings.errors import EmbeddingError
from app.embeddings.providers.deterministic import DeterministicEmbeddingProvider
from app.embeddings.providers.openai_compatible import OpenAICompatibleEmbeddingProvider
from app.embeddings.validation import validate_embeddings


async def test_deterministic_provider_is_stable_and_has_requested_dimension() -> None:
    provider = DeterministicEmbeddingProvider(16)
    first, second = await provider.embed(["tranquilo y luminoso", "tranquilo y luminoso"])
    assert first == second
    assert len(first) == 16
    assert any(value != 0 for value in first)


async def test_deterministic_provider_changes_with_input() -> None:
    provider = DeterministicEmbeddingProvider(16)
    first, second = await provider.embed(["cerca del mar", "patio amplio"])
    assert first != second


async def test_deterministic_provider_rejects_empty_degenerate_input() -> None:
    with pytest.raises(EmbeddingError) as caught:
        await DeterministicEmbeddingProvider(16).embed([""])
    assert caught.value.code == "invalid_embedding_zero_vector"


@pytest.mark.parametrize(
    "vector",
    [
        [0.0, 0.0],
        [True, 1.0],
        ["1", 2.0],
        [float("nan"), 1.0],
        [float("inf"), 1.0],
    ],
)
def test_generic_embedding_validation_rejects_unsafe_values(vector: list[object]) -> None:
    with pytest.raises(EmbeddingError):
        validate_embeddings([vector], expected_count=1, dimension=2)


def test_configured_embedding_dimension_must_match_vector_schema() -> None:
    with pytest.raises(ValidationError):
        Settings(embedding_dimension=768)


async def test_openai_compatible_provider_rejects_wrong_dimension() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-only"
        payload = json.loads(request.content)
        assert payload["dimensions"] == 4
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 2]}]})

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://provider.invalid/v1",
        api_key="test-only",
        model="fixture",
        dimension=4,
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(EmbeddingError, match="dimensión inválida"):
        await provider.embed(["texto"])


async def test_openai_compatible_timeout_is_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sensitive upstream detail", request=request)

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://provider.invalid/v1",
        api_key="test-only",
        model="fixture",
        dimension=4,
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(EmbeddingError) as caught:
        await provider.embed(["texto"])
    assert caught.value.code == "embedding_timeout"
    assert "sensitive" not in caught.value.safe_message


@pytest.mark.parametrize(
    ("data", "texts"),
    [
        ([{"index": 0, "embedding": [1, "not-a-number"]}], ["uno"]),
        ([{"index": 0, "embedding": 1}], ["uno"]),
        (
            [
                {"index": 0, "embedding": [1, 2]},
                {"index": 0, "embedding": [3, 4]},
            ],
            ["uno", "dos"],
        ),
        (
            [
                {"index": 0, "embedding": [1, 2]},
                {"index": 2, "embedding": [3, 4]},
            ],
            ["uno", "dos"],
        ),
    ],
)
async def test_openai_compatible_provider_rejects_malformed_rows(
    data: object,
    texts: list[str],
) -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://provider.invalid/v1",
        api_key="test-only",
        model="fixture",
        dimension=2,
        timeout_seconds=1,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"data": data})
        ),
    )

    with pytest.raises(EmbeddingError) as caught:
        await provider.embed(texts)

    assert caught.value.code in {"invalid_embedding_response", "invalid_embedding_values"}


@pytest.mark.parametrize(
    "embedding",
    [[0, 0], [True, 1], ["1", 1], [float("nan"), 1], [float("inf"), 1]],
)
async def test_openai_provider_rejects_non_cosine_safe_vectors(
    embedding: list[object],
) -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://provider.invalid/v1",
        api_key="test-only",
        model="fixture",
        dimension=2,
        timeout_seconds=1,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                content=json.dumps(
                    {"data": [{"index": 0, "embedding": embedding}]},
                    allow_nan=True,
                ).encode(),
                headers={"content-type": "application/json"},
            )
        ),
    )
    with pytest.raises(EmbeddingError):
        await provider.embed(["texto"])
