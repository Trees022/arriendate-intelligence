from collections.abc import Sequence

import httpx

from app.embeddings.errors import EmbeddingError
from app.embeddings.identity import embedding_space_id
from app.embeddings.validation import validate_embeddings


class OpenAICompatibleEmbeddingProvider:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dimension: int,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.space_id = embedding_space_id(
            provider=self.provider_name,
            model=model,
            dimension=dimension,
            endpoint=self.base_url,
        )

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": list(texts), "dimensions": self.dimension},
                )
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise EmbeddingError(
                "embedding_timeout",
                "El proveedor de embeddings agotó el tiempo de espera",
                timeout=True,
            ) from error
        except httpx.HTTPError as error:
            raise EmbeddingError(
                "embedding_provider_error", "El proveedor de embeddings no está disponible"
            ) from error

        try:
            payload = response.json()
            rows = payload["data"]
            if not isinstance(rows, list) or len(rows) != len(texts):
                raise ValueError("unexpected embedding row count")

            indexed_vectors: dict[int, list[object]] = {}
            for row in rows:
                if not isinstance(row, dict):
                    raise TypeError("embedding row must be an object")
                index = row["index"]
                raw_vector = row["embedding"]
                if type(index) is not int or index in indexed_vectors:
                    raise ValueError("embedding indices must be unique integers")
                if not isinstance(raw_vector, list):
                    raise TypeError("embedding must be an array")
                indexed_vectors[index] = raw_vector

            expected_indices = set(range(len(texts)))
            if set(indexed_vectors) != expected_indices:
                raise ValueError("embedding indices are incomplete")
            vectors = [indexed_vectors[index] for index in range(len(texts))]
        except (KeyError, TypeError, ValueError) as error:
            raise EmbeddingError(
                "invalid_embedding_response", "El proveedor devolvió embeddings inválidos"
            ) from error
        return validate_embeddings(
            vectors, expected_count=len(texts), dimension=self.dimension
        )
