import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_property_operations_vertical_slice_reaches_assisted_cooldown(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/properties",
        json={
            "title": "Casa piloto Castro",
            "description": "Casa con hechos verificados para validar el flujo operacional.",
            "operation_type": "rent",
            "property_type": "house",
            "city": "Castro",
            "sector": "Centro",
            "monthly_price": 720000,
            "sale_price": None,
            "currency": "CLP",
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 1,
            "pet_policy": "allowed",
            "furnished": False,
            "square_meters": 94,
            "reference_code": "PILOT-001",
            "built_area_m2": 94,
            "land_area_m2": 180,
            "commercial_status": "active",
            "amenities": ["patio", "bodega"],
        },
    )
    assert created.status_code == 201
    property_id = created.json()["id"]

    uploaded = await client.post(
        f"/api/properties/{property_id}/media",
        files={"file": ("fachada.jpg", b"fixture-jpeg-bytes", "image/jpeg")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["is_cover"] is True
    media = await client.get(uploaded.json()["url"])
    assert media.status_code == 200
    assert media.content == b"fixture-jpeg-bytes"

    package_response = await client.post(f"/api/properties/{property_id}/packages")
    assert package_response.status_code == 201
    package = package_response.json()
    assert {variant["channel_type"] for variant in package["variants"]} >= {
        "facebook_page",
        "instagram_professional",
        "facebook_group",
        "facebook_marketplace",
        "generic",
    }
    assert package["variants"][0]["suggested_media_ids"]

    approved = await client.patch(f"/api/packages/{package['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    target_response = await client.post(
        "/api/publication-targets",
        json={
            "name": "Grupo piloto Castro",
            "channel_type": "facebook_group",
            "execution_mode": "assisted",
            "destination_url": "https://example.invalid/facebook/groups/pilot-castro",
            "geographic_relevance": "Castro",
            "property_tags": ["casa", "arriendo"],
            "minimum_repost_interval_hours": 96,
        },
    )
    assert target_response.status_code == 201
    target = target_response.json()

    campaign_response = await client.post(
        "/api/campaigns",
        json={
            "property_id": property_id,
            "package_id": package["id"],
            "target_ids": [target["id"]],
        },
    )
    assert campaign_response.status_code == 201
    campaign = campaign_response.json()
    assert campaign["status"] == "active"
    assert campaign["jobs"][0]["status"] == "ready"
    assert campaign["jobs"][0]["execution_mode"] == "assisted"

    publication_response = await client.post(
        f"/api/publication-jobs/{campaign['jobs'][0]['id']}/publish",
        json={"publication_url": "https://example.invalid/publications/pilot-castro"},
    )
    assert publication_response.status_code == 200
    assert publication_response.json()["property_id"] == property_id

    command_center = await client.get(f"/api/properties/{property_id}/command-center")
    assert command_center.status_code == 200
    distribution = next(
        item
        for item in command_center.json()["distribution"]
        if item["target"]["id"] == target["id"]
    )
    assert distribution["status"] == "cooldown"
    assert distribution["next_eligible_at"] is not None
    assert distribution["prepared_media"][0]["is_cover"] is True

