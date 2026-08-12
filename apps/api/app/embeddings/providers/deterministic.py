import hashlib
import math
import re
import unicodedata
from collections.abc import Sequence

from app.embeddings.identity import embedding_space_id
from app.embeddings.validation import validate_embeddings

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalized_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return TOKEN_PATTERN.findall(ascii_text)


class DeterministicEmbeddingProvider:
    """Stable signed feature hashing for local tests; it is not a production semantic model."""

    provider_name = "deterministic"
    model = "deterministic-feature-hash-v1"

    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension
        self.space_id = embedding_space_id(
            provider=self.provider_name,
            model=self.model,
            dimension=dimension,
        )

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = [self._embed_one(text) for text in texts]
        return validate_embeddings(vectors, expected_count=len(texts), dimension=self.dimension)

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = normalized_tokens(text)
        features = tokens + [
            f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False)
        ]
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector
