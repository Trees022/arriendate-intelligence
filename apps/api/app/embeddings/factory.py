from app.core.settings import Settings
from app.embeddings.contracts import EmbeddingProvider
from app.embeddings.providers.deterministic import DeterministicEmbeddingProvider
from app.embeddings.providers.disabled import DisabledEmbeddingProvider
from app.embeddings.providers.openai_compatible import OpenAICompatibleEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider(settings.embedding_dimension)
    if settings.embedding_provider == "openai_compatible" and settings.embedding_api_key:
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key.get_secret_value(),
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    return DisabledEmbeddingProvider()
