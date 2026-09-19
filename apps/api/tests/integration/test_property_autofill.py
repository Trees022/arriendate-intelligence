import json
from pathlib import Path

import pytest

from app.ai.providers.fixture import StaticStructuredGenerator
from tests.factories import running_test_client


@pytest.mark.asyncio
async def test_property_autofill_returns_only_known_relevant_land_facts(
    tmp_path: Path,
) -> None:
    generator = StaticStructuredGenerator(
        json.dumps(
            {
                "operation_type": "buy",
                "property_type": "land",
                "title": None,
                "description": "Parcela de 5.000 m2 con luz y agua.",
                "price": 70_000_000,
                "currency": "CLP",
                "city": "Dalcahue",
                "sector": None,
                "address_text": None,
                "bedrooms": 3,
                "bathrooms": 2,
                "parking_spaces": None,
                "built_area_m2": 120,
                "land_area_m2": 5_000,
                "pet_policy": "allowed",
                "furnished": True,
                "amenities": ["luz", "agua"],
            }
        )
    )

    async with running_test_client(tmp_path, generator=generator) as client:
        response = await client.post(
            "/api/properties/autofill",
            json={
                "source_text": (
                    "Vendo parcela en Dalcahue, 5.000 m2, con luz y agua. "
                    "Precio $70.000.000."
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft"]["land_area_m2"] == 5_000
    assert payload["draft"]["bedrooms"] is None
    assert payload["draft"]["bathrooms"] is None
    assert payload["draft"]["built_area_m2"] is None
    assert payload["draft"]["pet_policy"] is None
    assert payload["draft"]["furnished"] is None
    assert "title" in payload["review_fields"]
    assert payload["provider"] == "fixture"
    assert generator.calls[0].schema_name == "property_autofill_draft"
    assert "Never guess" in generator.calls[0].messages[0].content


@pytest.mark.asyncio
async def test_property_autofill_keeps_unknown_facts_empty(tmp_path: Path) -> None:
    generator = StaticStructuredGenerator(
        json.dumps(
            {
                "operation_type": "rent",
                "property_type": "apartment",
                "title": None,
                "description": None,
                "price": None,
                "currency": None,
                "city": "Castro",
                "sector": None,
                "address_text": None,
                "bedrooms": None,
                "bathrooms": None,
                "parking_spaces": None,
                "built_area_m2": None,
                "land_area_m2": 400,
                "pet_policy": None,
                "furnished": None,
                "amenities": [],
            }
        )
    )

    async with running_test_client(tmp_path, generator=generator) as client:
        response = await client.post(
            "/api/properties/autofill",
            json={
                "source_text": "Se arrienda departamento en Castro. Consultar precio y detalles.",
            },
        )

    assert response.status_code == 200
    draft = response.json()["draft"]
    assert draft["price"] is None
    assert draft["bedrooms"] is None
    assert draft["land_area_m2"] is None
    assert set(response.json()["review_fields"]) == {"title", "price"}


@pytest.mark.asyncio
async def test_property_can_be_saved_with_only_business_essential_fields(
    tmp_path: Path,
) -> None:
    async with running_test_client(tmp_path) as client:
        response = await client.post(
            "/api/properties",
            json={
                "title": "Parcela en Dalcahue",
                "description": "",
                "operation_type": "buy",
                "property_type": "land",
                "city": "Dalcahue",
                "sale_price": 70_000_000,
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["description"] == "Parcela en Dalcahue"
    assert payload["bedrooms"] is None
