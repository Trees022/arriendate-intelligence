import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.ai.contracts import StructuredGenerator
from app.core.settings import Settings
from app.main import create_app

VALID_REQUIREMENTS: dict[str, Any] = {
    "operation_type": "rent",
    "property_types": ["apartment"],
    "locations": ["Viña del Mar"],
    "max_budget": 700_000,
    "currency": "CLP",
    "min_bedrooms": 2,
    "min_bathrooms": None,
    "parking_required": True,
    "pets_required": True,
    "furnished_preference": None,
    "soft_preferences": ["sector tranquilo", "apto para trabajar desde casa"],
    "missing_information": [],
    "confidence": 0.96,
}


def valid_requirements_json(**overrides: Any) -> str:
    payload = {**VALID_REQUIREMENTS, **overrides}
    return json.dumps(payload, ensure_ascii=False)


@asynccontextmanager
async def running_test_client(
    tmp_path: Path,
    *,
    generator: StructuredGenerator | None = None,
    database_url: str | None = None,
    **settings_overrides: Any,
) -> AsyncIterator[AsyncClient]:
    if database_url is None:
        database_path = (tmp_path / "test.db").as_posix()
        database_url = f"sqlite+aiosqlite:///{database_path}"
    settings_values: dict[str, Any] = {
        "database_url": database_url,
        "seed_demo_data": True,
        "cors_origins": ["http://test.local"],
    }
    settings_values.update(settings_overrides)
    settings = Settings(**settings_values)
    app = create_app(settings, structured_generator=generator)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test.local") as client:
            yield client
