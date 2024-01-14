import asyncio
from asyncio import AbstractEventLoop
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator, Any

import fakeredis
from fastapi_mail.email_utils import DefaultChecker
from httpx import AsyncClient
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.api.v1.dependencies import default_checker
from src.core.config import config
from src.database import get_async_session, Base
from src.main import app
from src.models.socials import SocialMedia
from src.models.users import User
from src.repositories.redis import get_redis, rate_limiter
from src.schemas.auth import Token


VERSION = 'api/v1/'

BASE_URL = f'http://testserver/{VERSION}'

ADMIN_USER = {
    'uuid': '5ad22093-194e-429c-b2af-cb531c7267c1',
    'username': 'admin',
    'email': 'admin@admin.com',
    'password': 'admin',
    'confirmed': True,
    'confirmed_on': datetime.now(),
    'active': True,
    'admin': True,
}
VERIFIED_USER = {
    'uuid': '950f8c5f-ad0c-4fb7-a693-dc42c7ea453a',
    'username': 'alice',
    'email': 'alice@alice.com',
    'password': 'alice',
    'confirmed': True,
    'confirmed_on': datetime.now(),
    'active': True,
    'admin': False,
}
UNVERIFIED_USER = {
    'uuid': '764a3113-7d87-4345-8c91-d68e2464b060',
    'username': 'bob',
    'email': 'bob@bob.com',
    'password': 'bob',
    'confirmed': False,
    'confirmed_on': None,
    'active': False,
    'admin': False,
}


async def create_user(user_type: dict[str, Any], async_session: AsyncSession) -> User:
    user = User(**user_type)
    social = SocialMedia(user_id=user.uuid)
    async_session.add(user)
    async_session.add(social)
    await async_session.commit()
    return user


async def create_token(user_type: dict[str, Any], async_client: AsyncClient) -> Token:
    data = {'username': user_type['username'], 'password': user_type['password']}
    resp = await async_client.post('auth/token', data=data)
    return Token.model_validate(resp.json())


engine_test = create_async_engine(config.POSTGRES_DSN, poolclass=NullPool)
async_session_maker = async_sessionmaker(engine_test, expire_on_commit=False, autoflush=False)
fake_redis_server = fakeredis.FakeServer()
fake_redis_client = fakeredis.aioredis.FakeRedis(server=fake_redis_server, decode_responses=False)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def override_default_checker() -> DefaultChecker:
    checker = DefaultChecker(db_provider='redis')
    checker.redis_client = fake_redis_client
    await checker.init_redis()
    return checker


app.dependency_overrides[get_async_session] = override_get_async_session
app.dependency_overrides[get_redis] = lambda: fake_redis_client
app.dependency_overrides[default_checker] = override_default_checker


@pytest.fixture(scope='function')
async def redis_client() -> fakeredis.aioredis.FakeRedis:
    return fake_redis_client


@pytest.fixture(autouse=True, scope='function')
def mock_rate_limiter(mocker: MockerFixture) -> fakeredis.aioredis.FakeRedis:
    redis_mock = fake_redis_client
    mocker.patch.object(rate_limiter, 'redis', redis_mock)
    return redis_mock


@pytest.fixture(autouse=True, scope='session')
async def prepare_database() -> AsyncGenerator[None, None]:
    assert Path.exists(config.ROOT_DIR.parent / '.test.env'), 'No testing enviroment'
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope='function')
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope='function')
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url=BASE_URL, follow_redirects=True) as client:
        await app.router.startup()
        yield client
        await app.router.shutdown()


@pytest.fixture(scope='session')
def event_loop() -> Generator[AbstractEventLoop, Any, None]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='function')
async def admin_user(async_session: AsyncSession) -> User:
    return await create_user(ADMIN_USER, async_session)


@pytest.fixture(scope='function')
async def verified_user(async_session: AsyncSession) -> User:
    return await create_user(VERIFIED_USER, async_session)


@pytest.fixture(scope='function')
async def unverified_user(async_session: AsyncSession) -> User:
    return await create_user(UNVERIFIED_USER, async_session)


@pytest.fixture(scope='function')
async def admin_token(async_client: AsyncClient) -> Token:
    return await create_token(ADMIN_USER, async_client)


@pytest.fixture(scope='function')
async def verified_user_token(async_client: AsyncClient) -> Token:
    return await create_token(VERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def unverified_user_token(async_client: AsyncClient) -> Token:
    return await create_token(UNVERIFIED_USER, async_client)
