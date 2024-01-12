from typing import AsyncIterator

from httpx import AsyncClient
import pytest

from src.main import app


BASE_URL = 'http://testserver/'


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url=BASE_URL, follow_redirects=True) as client:
        await app.router.startup()
        yield client
        await app.router.shutdown()
