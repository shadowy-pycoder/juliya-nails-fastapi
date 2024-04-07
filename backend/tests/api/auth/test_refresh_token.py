from datetime import datetime, timedelta

from fakeredis.aioredis import FakeRedis
from fastapi import status
from freezegun.api import FrozenDateTimeFactory
from httpx import AsyncClient
from src.core.config import config
from src.models.users import User
from src.schemas.auth import Token


async def test_refresh_access_token_anonymous(anonymous_user_token: str, async_client: AsyncClient) -> None:
    resp = await async_client.post('auth/refresh', headers={'refresh-token': anonymous_user_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_access_token_no_redis(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
    redis_client: FakeRedis,
) -> None:
    await redis_client.hdel(config.REDIS_HASH, str(verified_user.uuid))
    resp = await async_client.post('auth/refresh', headers={'refresh-token': verified_user_token.refresh_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_revoke_refresh_token_anonymous(anonymous_user_token: str, async_client: AsyncClient) -> None:
    resp = await async_client.post('auth/revoke', headers={'refresh-token': anonymous_user_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_access_token_with_expired_token(
    verified_user_token: Token, async_client: AsyncClient, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime.now() + timedelta(seconds=config.JWT_REFRESH_EXPIRATION + 1))
    resp = await async_client.post('auth/refresh', headers={'refresh-token': verified_user_token.refresh_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json() == {'detail': 'Invalid refresh token'}
