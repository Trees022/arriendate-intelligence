import math
from collections.abc import Sequence

from app.embeddings.errors import EmbeddingError


def validate_embeddings(
    vectors: Sequence[Sequence[object]], *, expected_count: int, dimension: int
) -> list[list[float]]:
    """Validate provider-independent vector invariants required by cosine similarity."""
    if len(vectors) != expected_count:
        raise EmbeddingError(
            "invalid_embedding_count",
            "El proveedor devolvió una cantidad inválida de embeddings",
        )

    validated: list[list[float]] = []
    for raw_vector in vectors:
        if (
            not isinstance(raw_vector, Sequence)
            or isinstance(raw_vector, (str, bytes))
            or len(raw_vector) != dimension
        ):
            raise EmbeddingError(
                "invalid_embedding_dimension",
                "El proveedor devolvió una dimensión inválida",
            )
        vector: list[float] = []
        for value in raw_vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EmbeddingError(
                    "invalid_embedding_values",
                    "El proveedor devolvió valores de embedding inválidos",
                )
            numeric = float(value)
            if not math.isfinite(numeric):
                raise EmbeddingError(
                    "invalid_embedding_values",
                    "El proveedor devolvió valores de embedding inválidos",
                )
            vector.append(numeric)
        if math.sqrt(sum(value * value for value in vector)) == 0:
            raise EmbeddingError(
                "invalid_embedding_zero_vector",
                "El proveedor devolvió un embedding sin norma útil",
            )
        validated.append(vector)
    return validated
