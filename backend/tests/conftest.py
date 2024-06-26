import asyncio
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

import fakeredis
import pytest
from httpx import AsyncClient, Timeout
from PIL import ImageFile
from pytest import FixtureRequest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import config
from src.database import Base, get_async_session
from src.main import app
from src.models.entries import Entry
from src.models.posts import Post
from src.models.services import Service
from src.models.users import User
from src.repositories.redis import get_redis, rate_limiter
from src.schemas.auth import Token
from tests.utils import (
    ADMIN_USER,
    BASE_URL,
    INACTIVE_USER,
    POSTS,
    SECOND_VERIFIED_USER,
    SERVICES,
    UNVERIFIED_USER,
    VERIFIED_USER,
    EntryFactory,
    EntryList,
    ImageFactory,
    T,
    create_entries,
    create_image,
    create_token,
    create_user,
    delete_user,
)


engine_test = create_async_engine(config.POSTGRES_DSN, poolclass=NullPool)
async_session_maker = async_sessionmaker(engine_test, expire_on_commit=False, autoflush=False)
fake_redis_server = fakeredis.FakeServer()
fake_redis_client = fakeredis.aioredis.FakeRedis(server=fake_redis_server, decode_responses=False)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session
app.dependency_overrides[get_redis] = lambda: fake_redis_client


@pytest.fixture(scope='function')
async def redis_client() -> fakeredis.aioredis.FakeRedis:
    return fake_redis_client


@pytest.fixture(autouse=True, scope='function')
def mock_rate_limiter(mocker: MockerFixture) -> fakeredis.aioredis.FakeRedis:
    redis_mock = fake_redis_client
    mocker.patch.object(rate_limiter, 'redis', redis_mock)
    return redis_mock


async def drop_all() -> None:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True, scope='session')
async def prepare_database() -> AsyncGenerator[None, None]:
    assert Path.exists(config.ROOT_DIR.parent / '.test.env'), 'No testing enviroment'
    await drop_all()
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await drop_all()


@pytest.fixture(scope='function')
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope='function')
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url=BASE_URL, follow_redirects=True, timeout=Timeout(15)) as client:
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
async def admin_user(async_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = await create_user(ADMIN_USER, async_session)
    yield user
    await delete_user(user, async_session)


@pytest.fixture(scope='function')
async def verified_user(async_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = await create_user(VERIFIED_USER, async_session)
    yield user
    await delete_user(user, async_session)


@pytest.fixture(scope='function')
async def second_verified_user(async_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = await create_user(SECOND_VERIFIED_USER, async_session)
    yield user
    await delete_user(user, async_session)


@pytest.fixture(scope='function')
async def unverified_user(async_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = await create_user(UNVERIFIED_USER, async_session)
    yield user
    await delete_user(user, async_session)


@pytest.fixture(scope='function')
async def inactive_user(async_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = await create_user(INACTIVE_USER, async_session)
    yield user
    await delete_user(user, async_session)


@pytest.fixture(scope='function')
async def admin_user_token(admin_user: User, async_client: AsyncClient) -> Token:
    return await create_token(admin_user, ADMIN_USER, async_client)


@pytest.fixture(scope='function')
async def verified_user_token(verified_user: User, async_client: AsyncClient) -> Token:
    return await create_token(verified_user, VERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def second_verified_user_token(second_verified_user: User, async_client: AsyncClient) -> Token:
    return await create_token(second_verified_user, SECOND_VERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def unverified_user_token(unverified_user: User, async_client: AsyncClient) -> Token:
    return await create_token(unverified_user, UNVERIFIED_USER, async_client)


@pytest.fixture(scope='function')
async def inactive_user_token(inactive_user: User, async_client: AsyncClient) -> Token:
    return await create_token(inactive_user, INACTIVE_USER, async_client)


@pytest.fixture(scope='function')
def anonymous_user_token() -> str:
    return 'fake_token'


@pytest.fixture(autouse=True, scope='session')
def load_truncate() -> Generator[None, None, None]:
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    yield
    ImageFile.LOAD_TRUNCATED_IMAGES = False


@pytest.fixture(scope='function')
def entry_factory(request: FixtureRequest) -> EntryFactory:
    async def inner(user: User, async_session: AsyncSession) -> AsyncGenerator[list[Entry], None]:
        return create_entries(user.uuid, request.param, async_session)

    return inner


@pytest.fixture(scope='function')
async def post_list(admin_user: User, async_session: AsyncSession) -> AsyncGenerator[list[Post], None]:
    posts = [Post(**data) for data in POSTS]
    async_session.add_all(posts)
    await async_session.commit()
    yield posts
    for post in posts:
        await async_session.delete(post)
    await async_session.commit()


@pytest.fixture(scope='function')
async def service_list(async_session: AsyncSession) -> AsyncGenerator[list[Service], None]:
    services = [Service(**data) for data in SERVICES]
    async_session.add_all(services)
    await async_session.commit()
    yield services
    for service in services:
        await async_session.delete(service)
    await async_session.commit()


@pytest.fixture(scope='function')
async def entry_list(service_list: list[Service], request: FixtureRequest) -> EntryList:
    services_uuid = [str(service.uuid) for service in service_list]
    total_duration = sum(service.duration for service in service_list)
    offset = total_duration - request.param['offset']
    date = datetime.now().replace(hour=12) + timedelta(days=request.param['days'])
    date_prev = date - timedelta(minutes=offset)
    date_next = date + timedelta(minutes=offset)
    data = {
        'date': date.date().isoformat(),
        'time': date.time().isoformat(),
        'services': services_uuid,
    }
    data_prev = {
        'date': date_prev.date().isoformat(),
        'time': date_prev.time().isoformat(),
        'services': services_uuid,
    }
    data_next = {
        'date': date_next.date().isoformat(),
        'time': date_next.time().isoformat(),
        'services': services_uuid,
    }
    return data, data_prev, data_next, date


@pytest.fixture(scope='function')
def image_factory(request: FixtureRequest) -> ImageFactory[T]:
    async def inner(
        *,
        fmt: str = 'png',
        size: int = config.IMAGE_SIZE,
        instance: T,
        async_session: AsyncSession | None = None,
    ) -> AsyncGenerator[tuple[str, Path, T], None]:
        return create_image(fmt, request.param, size, instance, async_session)

    return inner
