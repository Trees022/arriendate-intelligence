from httpx import AsyncClient


async def test_health_and_inventory_are_available(client: AsyncClient) -> None:
    health = await client.get("/api/health")
    inventory = await client.get("/api/properties")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "ready"}
    assert inventory.status_code == 200
    assert inventory.json()["total"] == 18
    assert len(inventory.json()["items"]) == 18


async def test_inventory_filters_and_exposes_unknown_values(client: AsyncClient) -> None:
    filtered = await client.get(
        "/api/properties",
        params={"operation_type": "rent", "city": "Quilpué", "availability": "available"},
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 2
    assert {item["title"] for item in payload["items"]} == {
        "Departamento El Belloto",
        "Departamento Valencia",
    }
    incomplete = next(item for item in payload["items"] if item["title"] == "Departamento Valencia")
    assert incomplete["bedrooms"] is None
    assert incomplete["parking_spaces"] is None
    assert incomplete["furnished"] is None


async def test_property_detail_does_not_expose_embedding(client: AsyncClient) -> None:
    response = await client.get("/api/properties/10000000-0000-4000-8000-000000000001")

    assert response.status_code == 200
    assert response.json()["title"] == "Departamento Los Castaños"
    assert "embedding" not in response.json()
    assert "embedding_text" not in response.json()
