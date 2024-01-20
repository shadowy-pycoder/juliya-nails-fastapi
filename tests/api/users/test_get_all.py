import pytest
from fastapi import status
from httpx import AsyncClient

from src.schemas.auth import Token


@pytest.mark.usefixtures(
    'clear_user_data', 'admin_user', 'verified_user', 'unverified_user', 'inactive_user'
)
async def test_get_all(
    admin_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'users', headers={'Authorization': f'Bearer {admin_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()['items']) == 4


async def test_get_all_non_admin(
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'users', headers={'Authorization': f'Bearer {verified_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json() == {'detail': 'You are not allowed to perform this operation'}


async def test_get_all_inactive_user(
    inactive_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'users', headers={'Authorization': f'Bearer {inactive_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json() == {
        'detail': 'Your account is inactive. Please activate your account to proceed.'
    }
