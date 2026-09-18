from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.enums import ChannelCapability, ChannelType


@dataclass(frozen=True, slots=True)
class PublishRequest:
    idempotency_key: str
    channel_type: ChannelType
    headline: str
    body: str
    media_urls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublishResult:
    external_publication_id: str
    publication_url: str | None
    published_at: datetime


@dataclass(frozen=True, slots=True)
class ExternalComment:
    external_id: str
    author_external_id: str | None
    author_display_name: str | None
    body: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExternalMessage:
    external_id: str
    conversation_external_id: str
    sender_external_id: str | None
    sender_display_name: str | None
    body: str | None
    sent_at: datetime


class SocialPublishingProvider(Protocol):
    @property
    def capabilities(self) -> frozenset[ChannelCapability]: ...

    async def publish(self, request: PublishRequest) -> PublishResult: ...


class EngagementProvider(Protocol):
    @property
    def capabilities(self) -> frozenset[ChannelCapability]: ...

    async def list_comments(self, external_publication_id: str) -> list[ExternalComment]: ...


class ConversationProvider(Protocol):
    @property
    def capabilities(self) -> frozenset[ChannelCapability]: ...

    async def list_messages(self, external_conversation_id: str) -> list[ExternalMessage]: ...

