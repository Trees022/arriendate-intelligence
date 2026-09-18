from uuid import UUID

import pytest
from httpx import AsyncClient

PROPERTY_ID = "10000000-0000-4000-8000-000000000001"


@pytest.mark.asyncio
async def test_command_center_aggregates_property_operations_without_fake_metrics(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/properties/{PROPERTY_ID}/command-center")
    assert response.status_code == 200
    payload = response.json()

    assert payload["property"]["id"] == PROPERTY_ID
    assert payload["demo_mode"] is True
    assert len(payload["channel_accounts"]) == 2
    assert len(payload["distribution"]) == 5

    groups = [
        item
        for item in payload["distribution"]
        if item["target"]["channel_type"] == "facebook_group"
    ]
    assert len(groups) == 2
    assert all(item["target"]["execution_mode"] == "assisted" for item in groups)
    assert all(
        next(
            capability
            for capability in item["capabilities"]
            if capability["capability"] == "publish_content"
        )["availability"]
        == "unavailable"
        for item in groups
    )

    assert payload["engagement"]["comments_count"] == 3
    assert payload["engagement"]["reactions_count"] == 11
    assert payload["engagement_snapshots"][2]["views_count"] is None
    assert payload["related_conversations"][0]["property_id"] == PROPERTY_ID
    assert payload["related_conversations"][0]["lead_id"] is None

    action_types = {item["type"] for item in payload["next_actions"]}
    assert {
        "initial_publication",
        "ready_to_repost",
        "conversation_needs_reply",
        "comment_needs_reply",
        "missing_marketing_data",
    } <= action_types


@pytest.mark.asyncio
async def test_assisted_job_completion_preserves_property_attribution_and_cooldown(
    client: AsyncClient,
) -> None:
    center = (await client.get(f"/api/properties/{PROPERTY_ID}/command-center")).json()
    marketplace = next(
        item
        for item in center["distribution"]
        if item["target"]["channel_type"] == "facebook_marketplace"
    )
    job_id = marketplace["job"]["id"]
    publish = await client.post(
        f"/api/publication-jobs/{job_id}/publish",
        json={
            "publication_url": "https://example.invalid/marketplace/demo-publication",
            "notes": "Publicación fixture completada por el operador.",
        },
    )
    assert publish.status_code == 200
    publication = publish.json()
    assert publication["property_id"] == PROPERTY_ID
    assert publication["target_id"] == marketplace["target"]["id"]
    assert publication["package_id"] == marketplace["job"]["package_id"]

    refreshed = (await client.get(f"/api/properties/{PROPERTY_ID}/command-center")).json()
    refreshed_marketplace = next(
        item
        for item in refreshed["distribution"]
        if item["target"]["channel_type"] == "facebook_marketplace"
    )
    assert refreshed_marketplace["status"] == "cooldown"
    assert refreshed_marketplace["next_eligible_at"] is not None


@pytest.mark.asyncio
async def test_property_change_generates_stale_package_action(client: AsyncClient) -> None:
    update = await client.patch(
        f"/api/properties/{PROPERTY_ID}",
        json={"title": "Departamento actualizado para prueba"},
    )
    assert update.status_code == 200
    center = (await client.get(f"/api/properties/{PROPERTY_ID}/command-center")).json()
    assert "stale_package" in {item["type"] for item in center["next_actions"]}


@pytest.mark.asyncio
async def test_assisted_job_can_record_required_action_and_sanitized_failure(
    client: AsyncClient,
) -> None:
    center = (await client.get(f"/api/properties/{PROPERTY_ID}/command-center")).json()
    marketplace = next(
        item
        for item in center["distribution"]
        if item["target"]["channel_type"] == "facebook_marketplace"
    )
    job_id = marketplace["job"]["id"]
    action = await client.post(
        f"/api/publication-jobs/{job_id}/requires-action",
        json={"note": "La plataforma solicitó revisión humana."},
    )
    assert action.status_code == 200
    assert action.json()["action_required"] is True

    failure = await client.post(
        f"/api/publication-jobs/{job_id}/fail",
        json={
            "error_code": "assisted_form_rejected",
            "error_message": "La plataforma rechazó el formulario asistido.",
        },
    )
    assert failure.status_code == 200
    assert failure.json()["status"] == "failed"
    assert failure.json()["attempt_count"] == 1


@pytest.mark.asyncio
async def test_unsupported_api_target_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/publication-targets",
        json={
            "name": "Grupo no soportado",
            "channel_type": "facebook_group",
            "execution_mode": "api",
            "minimum_repost_interval_hours": 72,
        },
    )
    assert response.status_code == 422
    assert "no admiten publicación API general" in response.text


@pytest.mark.asyncio
async def test_property_update_rejects_inconsistent_operation_prices(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/api/properties/{PROPERTY_ID}",
        json={"operation_type": "buy"},
    )
    assert response.status_code == 422
    unchanged = (await client.get(f"/api/properties/{PROPERTY_ID}")).json()
    assert unchanged["operation_type"] == "rent"
    assert unchanged["monthly_price"] == 670000


@pytest.mark.asyncio
async def test_paused_campaign_blocks_publication_until_resumed(client: AsyncClient) -> None:
    campaign_id = "40000000-0000-4000-8000-000000000001"
    center = (await client.get(f"/api/properties/{PROPERTY_ID}/command-center")).json()
    marketplace = next(
        item
        for item in center["distribution"]
        if item["target"]["channel_type"] == "facebook_marketplace"
    )
    pause = await client.post(f"/api/campaigns/{campaign_id}/pause")
    assert pause.status_code == 200
    duplicate_pause = await client.post(f"/api/campaigns/{campaign_id}/pause")
    assert duplicate_pause.status_code == 422

    blocked = await client.post(
        f"/api/publication-jobs/{marketplace['job']['id']}/publish",
        json={"publication_url": "https://example.invalid/blocked"},
    )
    assert blocked.status_code == 422
    resume = await client.post(f"/api/campaigns/{campaign_id}/resume")
    assert resume.status_code == 200


def test_demo_ids_are_valid_uuid_values() -> None:
    assert str(UUID(PROPERTY_ID)) == PROPERTY_ID
