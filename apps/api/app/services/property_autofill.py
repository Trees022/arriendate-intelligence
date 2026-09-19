from pydantic import ValidationError

from app.ai.contracts import StructuredGenerator
from app.ai.errors import ProviderError
from app.ai.property_autofill import (
    PropertyAutofillDraft,
    build_property_autofill_request,
)
from app.core.errors import (
    AIProviderResponseError,
    AIProviderUnavailableError,
    InvalidAIOutputError,
)


class PropertyAutofillService:
    def __init__(self, generator: StructuredGenerator) -> None:
        self.generator = generator

    async def extract(self, source_text: str) -> tuple[PropertyAutofillDraft, str, str]:
        request = build_property_autofill_request(source_text)
        try:
            result = await self.generator.generate_structured(request)
        except ProviderError as error:
            if error.code != "provider_not_configured" and not error.retryable:
                raise AIProviderResponseError(error.safe_message) from error
            raise AIProviderUnavailableError(
                error.safe_message,
                timeout=error.code == "provider_timeout",
            ) from error

        try:
            draft = PropertyAutofillDraft.model_validate_json(result.output_text)
        except ValidationError as error:
            raise InvalidAIOutputError from error
        return draft, result.provider, result.model

