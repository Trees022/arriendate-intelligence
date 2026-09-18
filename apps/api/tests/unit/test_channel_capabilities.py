from uuid import uuid4

import pytest

from app.domain.capabilities import (
    capabilities_for_account,
    capabilities_for_target,
    validate_execution_mode,
)
from app.domain.enums import (
    AccountType,
    CapabilityAvailability,
    ChannelCapability,
    ChannelType,
    ConnectionStatus,
    ExecutionMode,
)
from app.integrations.contracts import PublishRequest
from app.integrations.errors import UnsupportedCapabilityError
from app.integrations.meta import MetaPageFixtureAdapter


def _status_map(items):  # type: ignore[no-untyped-def]
    return {item.capability: item.availability for item in items}


def test_assisted_surfaces_never_claim_official_api_capabilities() -> None:
    for channel in (ChannelType.FACEBOOK_GROUP, ChannelType.FACEBOOK_MARKETPLACE):
        statuses = _status_map(capabilities_for_target(channel))
        assert statuses[ChannelCapability.ASSISTED_PUBLISH] == (
            CapabilityAvailability.ASSISTED_ONLY
        )
        assert statuses[ChannelCapability.PUBLISH_CONTENT] == (
            CapabilityAvailability.UNAVAILABLE
        )
        with pytest.raises(ValueError, match="no admiten publicación API general"):
            validate_execution_mode(channel, ExecutionMode.API)


def test_official_account_capabilities_depend_on_connection_state() -> None:
    connected = _status_map(
        capabilities_for_account(
            AccountType.FACEBOOK_PAGE,
            ConnectionStatus.CONNECTED,
        )
    )
    disconnected = _status_map(
        capabilities_for_account(
            AccountType.FACEBOOK_PAGE,
            ConnectionStatus.DISCONNECTED,
        )
    )
    assert connected[ChannelCapability.PUBLISH_CONTENT] == CapabilityAvailability.AVAILABLE
    assert connected[ChannelCapability.READ_MESSAGES] == CapabilityAvailability.AVAILABLE
    assert disconnected[ChannelCapability.PUBLISH_CONTENT] == (
        CapabilityAvailability.REQUIRES_CONNECTION
    )


@pytest.mark.asyncio
async def test_provider_rejects_channel_outside_its_surface() -> None:
    provider = MetaPageFixtureAdapter()
    request = PublishRequest(
        idempotency_key=str(uuid4()),
        channel_type=ChannelType.FACEBOOK_GROUP,
        headline="Demo",
        body="Contenido de prueba",
        media_urls=(),
    )
    with pytest.raises(UnsupportedCapabilityError):
        await provider.publish(request)

