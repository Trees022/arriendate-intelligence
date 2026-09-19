from app.domain.enums import ChannelType
from app.integrations.meta import build_meta_provider_boundary


def test_fixture_boundary_exposes_only_supported_official_meta_surfaces() -> None:
    boundary = build_meta_provider_boundary("fixture")

    assert boundary.publishing_for(ChannelType.FACEBOOK_PAGE) is not None
    assert boundary.publishing_for(ChannelType.INSTAGRAM_PROFESSIONAL) is not None
    assert boundary.conversations_for(ChannelType.MESSENGER) is not None
    assert boundary.conversations_for(ChannelType.INSTAGRAM_PROFESSIONAL) is not None
    assert boundary.publishing_for(ChannelType.FACEBOOK_GROUP) is None
    assert boundary.publishing_for(ChannelType.FACEBOOK_MARKETPLACE) is None


def test_disabled_boundary_is_safe_without_credentials() -> None:
    boundary = build_meta_provider_boundary("disabled")

    assert boundary.publishing_for(ChannelType.FACEBOOK_PAGE) is None
    assert boundary.conversations_for(ChannelType.MESSENGER) is None
