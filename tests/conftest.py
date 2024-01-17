import asyncio
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import AsyncGenerator, Generator, Any

import fakeredis
from fastapi_mail.email_utils import DefaultChecker
from httpx import AsyncClient
import pytest
from pytest_mock import MockerFixture
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.api.v1.dependencies import default_checker
from src.core.config import config
from src.database import get_async_session, Base
from src.main import app
from src.repositories.redis import get_redis, rate_limiter
from src.schemas.auth import Token
from tests.utils import (
    ADMIN_USER,
    VERIFIED_USER,
    UNVERIFIED_USER,
    INACTIVE_USER,
    BASE_URL,
    contruct_query,
    create_token,
)


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
        await conn.execute(
            sa.text(
                """INSERT INTO "user" 
                (uuid, email, hashed_password, username, confirmed, confirmed_on, active, admin)
                VALUES (:uuid, :email, :hashed_password, :username, :confirmed, :confirmed_on, :active, :admin);"""
            ),
            [
                {**contruct_query(user)}
                for user in [ADMIN_USER, VERIFIED_USER, UNVERIFIED_USER, INACTIVE_USER]
            ],
        )
        await conn.execute(
            sa.text(
                f"""INSERT INTO "social" (uuid, user_id, avatar)
                VALUES (gen_random_uuid(), '{ADMIN_USER['uuid']}', 'default.jpg'),
                        (gen_random_uuid(), '{VERIFIED_USER['uuid']}', 'default.jpg'),
                        (gen_random_uuid(), '{UNVERIFIED_USER['uuid']}', 'default.jpg'),
                        (gen_random_uuid(), '{INACTIVE_USER['uuid']}', 'default.jpg');"""
            )
        )
        await conn.commit()
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
async def admin_token(async_client: AsyncClient) -> Token:
    return await create_token(ADMIN_USER, async_client)


@pytest.fixture(scope='function')
async def verified_user_token(async_client: AsyncClient) -> Token:
    return await create_token(VERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def unverified_user_token(async_client: AsyncClient) -> Token:
    return await create_token(UNVERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def inactive_user_token(async_client: AsyncClient) -> Token:
    return await create_token(INACTIVE_USER, async_client)


@pytest.fixture(scope='function')
def anonymous_user_token() -> str:
    return 'fake_token'
