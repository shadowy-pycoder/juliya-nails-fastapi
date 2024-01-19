import pytest
from fastapi import status
from httpx import AsyncClient

from src.models.users import User
from src.schemas.auth import Token
from src.schemas.users import UserRead


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


async def test_get_me(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'users/me', headers={'Authorization': f'Bearer {verified_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    user = UserRead(**resp.json())
    assert user.username == verified_user.username
    assert user.email == verified_user.email


async def test_update_me(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    data = {
        'username': 'new_username',
        'email': 'new_email@example.com',
        'password': 'foo#Bar1',
        'confirm_password': 'foo#Bar1',
    }
    resp = await async_client.put(
        'users/me',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    user = UserRead(**resp.json())
    assert user.username == data['username']
    assert user.email == data['email']
    assert user.confirmed is False
    assert user.confirmed_on is None
    assert user.active == verified_user.active
    assert user.admin == verified_user.admin
    assert user.created == verified_user.created
    assert user.updated > verified_user.updated


async def test_patch_me_no_email(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    data = {
        'username': 'new_username',
        'password': 'foo#Bar1',
        'confirm_password': 'foo#Bar1',
    }
    resp = await async_client.patch(
        'users/me',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    user = UserRead(**resp.json())
    assert user.username == data['username']
    assert user.email == verified_user.email
    assert user.confirmed is True
    assert user.confirmed_on == verified_user.confirmed_on
    assert user.active == verified_user.active
    assert user.admin == verified_user.admin
    assert user.created == verified_user.created
    assert user.updated > verified_user.updated


@pytest.mark.parametrize(
    'password, confirm_password, message',
    [
        ('foo#Bar1', 'foo#Bar2', 'Passwords do not match'),
        (None, 'foo#Bar2', 'Password field is missing'),
        ('foo#Bar1', None, 'Confirm password field is missing'),
    ],
)
async def test_patch_me_passwords(
    password: str | None,
    confirm_password: str | None,
    message: str,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    data = {
        'username': 'new_username',
        'password': password,
        'confirm_password': confirm_password,
    }
    resp = await async_client.patch(
        'users/me',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.json()['detail'][0]['msg'] == f'Value error, {message}'
