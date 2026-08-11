import os
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.supabase

APPLICATION_TABLES = ("leads", "lead_requirements", "ai_runs", "properties")


@dataclass(frozen=True, slots=True)
class LocalSupabase:
    url: str
    anon_key: str
    service_role_key: str


@pytest.fixture(scope="session")
def local_supabase() -> LocalSupabase:
    variable_names = (
        "ARRIENDATE_TEST_SUPABASE_URL",
        "ARRIENDATE_TEST_SUPABASE_ANON_KEY",
        "ARRIENDATE_TEST_SUPABASE_SERVICE_ROLE_KEY",
    )
    values = {name: os.getenv(name) for name in variable_names}
    if not all(values.values()):
        pytest.skip("local Supabase URL and ephemeral test keys are required")

    url = values["ARRIENDATE_TEST_SUPABASE_URL"]
    assert url is not None
    if urlparse(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Supabase integration tests refuse non-local URLs", pytrace=False)

    anon_key = values["ARRIENDATE_TEST_SUPABASE_ANON_KEY"]
    service_role_key = values["ARRIENDATE_TEST_SUPABASE_SERVICE_ROLE_KEY"]
    assert anon_key is not None
    assert service_role_key is not None
    return LocalSupabase(url.rstrip("/"), anon_key, service_role_key)


def role_headers(api_key: str, token: str) -> dict[str, str]:
    return {"apikey": api_key, "Authorization": f"Bearer {token}"}


async def create_authenticated_token(client: AsyncClient, anon_key: str) -> str:
    response = await client.post(
        "/auth/v1/signup",
        headers={"apikey": anon_key},
        json={
            "email": f"supabase-security-{uuid4().hex}@example.test",
            "password": "Local-only-Validation-2026!",
        },
    )
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert isinstance(token, str) and token
    return token


async def test_anon_openapi_does_not_publish_application_tables(
    local_supabase: LocalSupabase,
) -> None:
    async with AsyncClient(base_url=local_supabase.url, timeout=15) as client:
        response = await client.get(
            "/rest/v1/",
            headers=role_headers(local_supabase.anon_key, local_supabase.anon_key),
        )

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths) == {"/"}
    assert not any(f"/{table}" in paths for table in APPLICATION_TABLES)


async def test_data_api_roles_cannot_read_application_tables(
    local_supabase: LocalSupabase,
) -> None:
    async with AsyncClient(base_url=local_supabase.url, timeout=15) as client:
        authenticated_token = await create_authenticated_token(client, local_supabase.anon_key)
        roles = {
            "anon": (local_supabase.anon_key, local_supabase.anon_key, 401),
            "authenticated": (local_supabase.anon_key, authenticated_token, 403),
            "service_role": (
                local_supabase.service_role_key,
                local_supabase.service_role_key,
                403,
            ),
        }
        for api_key, token, expected_status in roles.values():
            for table in APPLICATION_TABLES:
                response = await client.get(
                    f"/rest/v1/{table}?select=*",
                    headers=role_headers(api_key, token),
                )
                assert response.status_code == expected_status


async def test_data_api_roles_cannot_insert_sensitive_leads(
    local_supabase: LocalSupabase,
) -> None:
    async with AsyncClient(base_url=local_supabase.url, timeout=15) as client:
        authenticated_token = await create_authenticated_token(client, local_supabase.anon_key)
        roles = {
            "anon": (local_supabase.anon_key, local_supabase.anon_key, 401),
            "authenticated": (local_supabase.anon_key, authenticated_token, 403),
            "service_role": (
                local_supabase.service_role_key,
                local_supabase.service_role_key,
                403,
            ),
        }
        for api_key, token, expected_status in roles.values():
            response = await client.post(
                "/rest/v1/leads",
                headers=role_headers(api_key, token),
                json={
                    "original_request": "Solicitud sintética local sin datos reales.",
                    "idempotency_key": str(uuid4()),
                },
            )
            assert response.status_code == expected_status
