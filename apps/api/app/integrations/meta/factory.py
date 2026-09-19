from dataclasses import dataclass, field
from typing import Literal

from app.domain.enums import ChannelType
from app.integrations.contracts import ConversationProvider, SocialPublishingProvider
from app.integrations.meta.fixtures import (
    InstagramFixtureAdapter,
    MetaMessengerFixtureAdapter,
    MetaPageFixtureAdapter,
)


@dataclass(frozen=True, slots=True)
class MetaProviderBoundary:
    """Official Meta surfaces only; assisted channels deliberately stay outside it.

    A future Graph API adapter is injected here on the server after account consent.
    Browser clients never receive credentials and Groups/Marketplace are never routed here.
    """

    publishing: dict[ChannelType, SocialPublishingProvider] = field(default_factory=dict)
    conversations: dict[ChannelType, ConversationProvider] = field(default_factory=dict)

    def publishing_for(self, channel_type: ChannelType) -> SocialPublishingProvider | None:
        return self.publishing.get(channel_type)

    def conversations_for(self, channel_type: ChannelType) -> ConversationProvider | None:
        return self.conversations.get(channel_type)


def build_meta_provider_boundary(
    mode: Literal["disabled", "fixture"],
) -> MetaProviderBoundary:
    if mode == "disabled":
        return MetaProviderBoundary()

    page = MetaPageFixtureAdapter()
    instagram = InstagramFixtureAdapter()
    messenger = MetaMessengerFixtureAdapter()
    return MetaProviderBoundary(
        publishing={
            ChannelType.FACEBOOK_PAGE: page,
            ChannelType.INSTAGRAM_PROFESSIONAL: instagram,
        },
        conversations={
            ChannelType.MESSENGER: messenger,
            ChannelType.INSTAGRAM_PROFESSIONAL: instagram,
        },
    )
