from app.ai.contracts import StructuredGenerator
from app.ai.providers.disabled import DisabledStructuredGenerator
from app.ai.providers.openai_compatible import OpenAICompatibleStructuredGenerator
from app.core.settings import Settings


def build_structured_generator(settings: Settings) -> StructuredGenerator:
    if settings.ai_provider == "disabled" or settings.ai_api_key is None:
        return DisabledStructuredGenerator()
    return OpenAICompatibleStructuredGenerator(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key.get_secret_value(),
        model=settings.ai_chat_model,
        reasoning_effort=settings.ai_reasoning_effort,
        timeout_seconds=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )
