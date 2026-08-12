from collections.abc import Sequence

from app.embeddings.errors import EmbeddingNotConfiguredError
from app.embeddings.identity import embedding_space_id


class DisabledEmbeddingProvider:
    provider_name = "disabled"
    model = "disabled"
    dimension = 1536
    space_id = embedding_space_id(
        provider=provider_name,
        model=model,
        dimension=dimension,
    )

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingNotConfiguredError()
