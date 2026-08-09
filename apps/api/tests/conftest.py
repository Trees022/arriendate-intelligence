from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.settings import Settings
from app.main import create_app


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_path = (tmp_path / "test.db").as_posix()
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{database_path}",
        seed_demo_data=True,
        cors_origins=["http://test.local"],
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test.local") as test_client:
            yield test_client
