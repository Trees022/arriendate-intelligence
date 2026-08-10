from app.ai.contracts import (
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from app.ai.errors import ProviderNotConfiguredError


class DisabledStructuredGenerator:
    @property
    def provider_name(self) -> str:
        return "disabled"

    @property
    def model(self) -> str:
        return "not-configured"

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        del request
        raise ProviderNotConfiguredError
