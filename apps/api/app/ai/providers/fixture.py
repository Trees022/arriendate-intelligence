from app.ai.contracts import (
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from app.ai.errors import ProviderError


class StaticStructuredGenerator:
    """Deterministic provider used only by tests and offline evaluations."""

    def __init__(
        self,
        output_text: str,
        *,
        error: ProviderError | None = None,
        input_tokens: int = 120,
        output_tokens: int = 80,
    ) -> None:
        self.output_text = output_text
        self.error = error
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[StructuredGenerationRequest] = []

    @property
    def provider_name(self) -> str:
        return "fixture"

    @property
    def model(self) -> str:
        return "fixture-structured-v1"

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        self.calls.append(request)
        if self.error:
            raise self.error
        return StructuredGenerationResult(
            output_text=self.output_text,
            provider=self.provider_name,
            model=self.model,
            provider_request_id="fixture-request-1",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )
