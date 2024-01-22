from pathlib import Path

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config
from src.models.users import User
from src.schemas.auth import Token
from src.schemas.socials import SocialRead
from src.schemas.users import UserRead
from tests.utils import SOCIAL_DATA, EntryFactory, ImageFactory, PostFactory, create_temp_image


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


@pytest.mark.parametrize('entry_factory, expected', [(0, 0), (5, 5)], indirect=['entry_factory'])
async def test_get_my_entries(
    verified_user: User,
    verified_user_token: Token,
    entry_factory: EntryFactory,
    expected: int,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    await entry_factory(verified_user, async_session)
    resp = await async_client.get(
        'users/me/entries', headers={'Authorization': f'Bearer {verified_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['total'] == expected


@pytest.mark.parametrize('post_factory, expected', [(0, 0), (5, 5)], indirect=['post_factory'])
async def test_get_my_posts(
    admin_user: User,
    admin_user_token: Token,
    post_factory: PostFactory,
    expected: int,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    await post_factory(admin_user, async_session)
    resp = await async_client.get(
        'users/me/posts', headers={'Authorization': f'Bearer {admin_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['total'] == expected


async def test_get_my_socials(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'users/me/socials', headers={'Authorization': f'Bearer {verified_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['user']['uuid'] == verified_user.uuid


async def test_update_my_socials(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    resp = await async_client.put(
        'users/me/socials',
        json=SOCIAL_DATA,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = SocialRead(**resp.json())
    await async_session.refresh(verified_user)
    for k, v in SOCIAL_DATA.items():
        assert getattr(resp_data, k) == v
        assert getattr(verified_user.socials, k) == v


async def test_patch_my_socials(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    data = {
        'first_name': 'John',
        'last_name': 'Doe',
    }
    resp = await async_client.patch(
        'users/me/socials',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = SocialRead(**resp.json())
    await async_session.refresh(verified_user)
    for k, v in data.items():
        assert getattr(resp_data, k) == v
        assert getattr(verified_user.socials, k) == v


@pytest.mark.parametrize('image_factory', [('profiles')], indirect=True)
async def test_get_my_avatar(
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    filename, img_path = await image_factory(instance=verified_user, async_session=async_session)
    resp = await async_client.get(
        'users/me/socials/avatar',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert verified_user.socials.avatar == filename
    assert Path.exists(img_path)
    Path.unlink(img_path)


@pytest.mark.parametrize('image_factory', [('profiles')], indirect=True)
async def test_update_my_avatar(
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    old_filename, old_img_path = await image_factory(
        instance=verified_user, async_session=async_session
    )
    img = create_temp_image()
    resp = await async_client.put(
        'users/me/socials/avatar',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        files={'file': (img.name, img, 'image/png')},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = SocialRead(**resp.json())
    await async_session.refresh(verified_user)
    assert verified_user.socials.avatar == resp_data.avatar
    assert resp_data.avatar != old_filename
    assert Path.exists(old_img_path.parent / resp_data.avatar)
    assert not Path.exists(old_img_path)
    Path.unlink(old_img_path.parent / resp_data.avatar)


@pytest.mark.parametrize('image_factory', [('profiles')], indirect=True)
async def test_delete_my_avatar(
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    filename, img_path = await image_factory(instance=verified_user, async_session=async_session)
    assert verified_user.socials.avatar == filename
    resp = await async_client.delete(
        'users/me/socials/avatar',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    await async_session.refresh(verified_user)
    assert verified_user.socials.avatar == config.DEFAULT_AVATAR
    assert not Path.exists(img_path)
