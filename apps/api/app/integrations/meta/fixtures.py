from datetime import UTC, datetime

from app.domain.enums import ChannelCapability, ChannelType
from app.integrations.contracts import (
    ExternalComment,
    ExternalMessage,
    PublishRequest,
    PublishResult,
)
from app.integrations.errors import UnsupportedCapabilityError


class _FixtureBase:
    capabilities: frozenset[ChannelCapability] = frozenset()

    def _require(self, capability: ChannelCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapabilityError


class MetaPageFixtureAdapter(_FixtureBase):
    """Deterministic Page fixture. It never calls Meta or stores credentials."""

    capabilities = frozenset(
        {
            ChannelCapability.PUBLISH_CONTENT,
            ChannelCapability.READ_COMMENTS,
            ChannelCapability.REPLY_COMMENTS,
            ChannelCapability.READ_REACTIONS,
            ChannelCapability.READ_METRICS,
        }
    )

    async def publish(self, request: PublishRequest) -> PublishResult:
        self._require(ChannelCapability.PUBLISH_CONTENT)
        if request.channel_type != ChannelType.FACEBOOK_PAGE:
            raise UnsupportedCapabilityError
        external_id = f"fixture-page-{request.idempotency_key}"
        return PublishResult(
            external_publication_id=external_id,
            publication_url=f"https://example.invalid/meta/page/{external_id}",
            published_at=datetime.now(UTC),
        )

    async def list_comments(self, external_publication_id: str) -> list[ExternalComment]:
        self._require(ChannelCapability.READ_COMMENTS)
        return []


class MetaMessengerFixtureAdapter(_FixtureBase):
    """Page Messenger boundary; intentionally separate from Page publishing."""

    capabilities = frozenset(
        {ChannelCapability.READ_MESSAGES, ChannelCapability.SEND_MESSAGES}
    )

    async def list_messages(self, external_conversation_id: str) -> list[ExternalMessage]:
        self._require(ChannelCapability.READ_MESSAGES)
        return []


class InstagramFixtureAdapter(_FixtureBase):
    """Instagram Professional fixture with its own capability surface."""

    capabilities = frozenset(
        {
            ChannelCapability.PUBLISH_CONTENT,
            ChannelCapability.READ_COMMENTS,
            ChannelCapability.REPLY_COMMENTS,
            ChannelCapability.READ_MESSAGES,
            ChannelCapability.SEND_MESSAGES,
            ChannelCapability.READ_METRICS,
        }
    )

    async def publish(self, request: PublishRequest) -> PublishResult:
        self._require(ChannelCapability.PUBLISH_CONTENT)
        if request.channel_type != ChannelType.INSTAGRAM_PROFESSIONAL:
            raise UnsupportedCapabilityError
        external_id = f"fixture-instagram-{request.idempotency_key}"
        return PublishResult(
            external_publication_id=external_id,
            publication_url=f"https://example.invalid/instagram/{external_id}",
            published_at=datetime.now(UTC),
        )

    async def list_comments(self, external_publication_id: str) -> list[ExternalComment]:
        self._require(ChannelCapability.READ_COMMENTS)
        return []

    async def list_messages(self, external_conversation_id: str) -> list[ExternalMessage]:
        self._require(ChannelCapability.READ_MESSAGES)
        return []
