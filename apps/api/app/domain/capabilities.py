from dataclasses import dataclass

from app.domain.enums import (
    AccountType,
    CapabilityAvailability,
    ChannelCapability,
    ChannelType,
    ConnectionStatus,
    ExecutionMode,
)


@dataclass(frozen=True, slots=True)
class CapabilityStatus:
    capability: ChannelCapability
    availability: CapabilityAvailability
    reason: str | None = None


_OFFICIAL_CAPABILITIES: dict[AccountType, frozenset[ChannelCapability]] = {
    AccountType.FACEBOOK_PAGE: frozenset(
        {
            ChannelCapability.PUBLISH_CONTENT,
            ChannelCapability.READ_COMMENTS,
            ChannelCapability.REPLY_COMMENTS,
            ChannelCapability.READ_MESSAGES,
            ChannelCapability.SEND_MESSAGES,
            ChannelCapability.READ_REACTIONS,
            ChannelCapability.READ_METRICS,
            ChannelCapability.SCHEDULE_CONTENT,
            ChannelCapability.AUTOMATIC_REPOST,
        }
    ),
    AccountType.INSTAGRAM_PROFESSIONAL: frozenset(
        {
            ChannelCapability.PUBLISH_CONTENT,
            ChannelCapability.READ_COMMENTS,
            ChannelCapability.REPLY_COMMENTS,
            ChannelCapability.READ_MESSAGES,
            ChannelCapability.SEND_MESSAGES,
            ChannelCapability.READ_METRICS,
            ChannelCapability.SCHEDULE_CONTENT,
        }
    ),
}

_ASSISTED_CHANNELS = frozenset(
    {ChannelType.FACEBOOK_GROUP, ChannelType.FACEBOOK_MARKETPLACE}
)


def capabilities_for_account(
    account_type: AccountType,
    connection_status: ConnectionStatus,
) -> list[CapabilityStatus]:
    supported = _OFFICIAL_CAPABILITIES[account_type]
    connected = connection_status in {
        ConnectionStatus.CONNECTED,
        ConnectionStatus.FIXTURE,
    }
    statuses: list[CapabilityStatus] = []
    for capability in ChannelCapability:
        if capability == ChannelCapability.ASSISTED_PUBLISH:
            statuses.append(
                CapabilityStatus(
                    capability,
                    CapabilityAvailability.UNAVAILABLE,
                    "Las cuentas oficiales usan un proveedor API, no el flujo asistido.",
                )
            )
        elif capability not in supported:
            statuses.append(
                CapabilityStatus(capability, CapabilityAvailability.UNAVAILABLE)
            )
        elif connected:
            statuses.append(
                CapabilityStatus(capability, CapabilityAvailability.AVAILABLE)
            )
        else:
            statuses.append(
                CapabilityStatus(
                    capability,
                    CapabilityAvailability.REQUIRES_CONNECTION,
                    "Conecta la cuenta oficial y concede los permisos requeridos.",
                )
            )
    return statuses


def capabilities_for_target(channel_type: ChannelType) -> list[CapabilityStatus]:
    if channel_type in _ASSISTED_CHANNELS:
        return [
            CapabilityStatus(
                capability,
                (
                    CapabilityAvailability.ASSISTED_ONLY
                    if capability == ChannelCapability.ASSISTED_PUBLISH
                    else CapabilityAvailability.UNAVAILABLE
                ),
                (
                    "Arriendate prepara el contenido; el operador publica en la plataforma."
                    if capability == ChannelCapability.ASSISTED_PUBLISH
                    else None
                ),
            )
            for capability in ChannelCapability
        ]

    return [
        CapabilityStatus(
            capability,
            CapabilityAvailability.REQUIRES_CONNECTION,
            "La capacidad depende de una cuenta conectada y sus permisos.",
        )
        for capability in ChannelCapability
    ]


def validate_execution_mode(
    channel_type: ChannelType,
    execution_mode: ExecutionMode,
) -> None:
    if channel_type in _ASSISTED_CHANNELS and execution_mode == ExecutionMode.API:
        raise ValueError(
            "Facebook Groups y Marketplace no admiten publicación API general; "
            "usa assisted, manual o local_agent."
        )


def can_execute_server_side(channel_type: ChannelType) -> bool:
    return channel_type in {
        ChannelType.FACEBOOK_PAGE,
        ChannelType.INSTAGRAM_PROFESSIONAL,
    }

