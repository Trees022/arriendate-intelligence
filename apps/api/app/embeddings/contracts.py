from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    @property
    def space_id(self) -> str: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
