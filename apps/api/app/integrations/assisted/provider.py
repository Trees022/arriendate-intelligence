from app.domain.enums import ChannelCapability
from app.integrations.contracts import PublishRequest, PublishResult
from app.integrations.errors import UnsupportedCapabilityError


class AssistedPublishingProvider:
    """Preparation boundary. External publication always remains a human action."""

    capabilities = frozenset({ChannelCapability.ASSISTED_PUBLISH})

    async def publish(self, request: PublishRequest) -> PublishResult:
        raise UnsupportedCapabilityError(
            "El flujo asistido no puede publicar automáticamente en la plataforma."
        )

