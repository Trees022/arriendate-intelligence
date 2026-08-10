from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.factories import running_test_client


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    async with running_test_client(tmp_path) as test_client:
        yield test_client
