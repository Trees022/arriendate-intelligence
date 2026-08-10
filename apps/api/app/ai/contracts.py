from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class PromptMessage:
    role: Literal["developer", "user"]
    content: str


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest:
    messages: tuple[PromptMessage, ...]
    schema_name: str
    schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StructuredGenerationResult:
    output_text: str
    provider: str
    model: str
    provider_request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class StructuredGenerator(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult: ...
