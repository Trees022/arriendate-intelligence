from uuid import uuid4

from httpx import AsyncClient


async def test_lead_is_persisted_before_any_processing(client: AsyncClient) -> None:
    original_request = (
        "  Somos una pareja con un perro. Buscamos departamento tranquilo en Viña del Mar.\n"
        "Presupuesto máximo: $700.000.  "
    )
    idempotency_key = str(uuid4())
    payload = {
        "name": "Camila y Tomás",
        "email": "DEMO@EJEMPLO.CL",
        "phone": "+56 9 0000 0000",
        "original_request": original_request,
    }

    created = await client.post(
        "/api/leads",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )
    assert created.status_code == 201
    lead = created.json()
    assert lead["original_request"] == original_request
    assert lead["email"] == "demo@ejemplo.cl"
    assert lead["status"] == "new"

    loaded = await client.get(f"/api/leads/{lead['id']}")
    assert loaded.status_code == 200
    assert loaded.json() == lead

    duplicate = await client.post(
        "/api/leads",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == lead["id"]


async def test_idempotency_key_cannot_be_reused_for_different_content(client: AsyncClient) -> None:
    idempotency_key = str(uuid4())
    first = await client.post(
        "/api/leads",
        json={"original_request": "Busco departamento de dos dormitorios en Concón."},
        headers={"Idempotency-Key": idempotency_key},
    )
    second = await client.post(
        "/api/leads",
        json={"original_request": "Busco una casa en Quilpué con patio y estacionamiento."},
        headers={"Idempotency-Key": idempotency_key},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "La clave de idempotencia ya fue usada con otra solicitud"


async def test_blank_or_malformed_lead_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/leads",
        json={"original_request": "             ", "unexpected": "value"},
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == 422
