from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config
from src.models.users import User
from src.schemas.auth import Token
from src.schemas.socials import SocialRead
from src.schemas.users import UserRead
from tests.utils import (
    ANONYMOUS_USER,
    SOCIAL_DATA,
    EntryFactory,
    ImageFactory,
    create_temp_image,
    create_user,
)


async def test_get_one(
    admin_user: User,
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        f'users/{verified_user.uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    user = UserRead(**resp.json())
    assert user.username == verified_user.username
    assert user.email == verified_user.email
    resp = await async_client.get(
        f'users/{ANONYMOUS_USER["uuid"]}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.json() == {'detail': 'User does not exist'}
    resp = await async_client.get(
        f'users/{admin_user.uuid}',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json() == {'detail': 'You are not allowed to perform this operation'}


async def test_update_one(
    admin_user_token: Token,
    verified_user: User,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    data = {
        'email': 'test@test.com',
        'username': 'test',
        'password': '12345678',
        'created': datetime.now(tz=timezone.utc).isoformat(),
        'confirmed': False,
        'confirmed_on': None,
        'active': False,
        'admin': False,
    }
    resp = await async_client.put(
        f'users/{verified_user.uuid}',
        json=data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = UserRead(**resp.json())
    await async_session.refresh(verified_user)
    for k, v in data.items():
        if k in ['password', 'created']:
            continue
        assert getattr(resp_data, k) == v
        assert getattr(verified_user, k) == v


async def test_patch_one(
    admin_user_token: Token,
    verified_user: User,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    old_data = verified_user.as_dict()
    new_data = {
        'email': 'test@test.com',
        'username': 'test',
    }
    resp = await async_client.patch(
        f'users/{verified_user.uuid}',
        json=new_data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = UserRead(**resp.json())
    await async_session.refresh(verified_user)
    assert resp_data.email == new_data['email']
    assert resp_data.username == new_data['username']
    assert verified_user.email == new_data['email']
    assert verified_user.username == new_data['username']
    assert verified_user.confirmed == old_data['confirmed']
    assert verified_user.confirmed_on == old_data['confirmed_on']
    assert verified_user.active == old_data['active']
    assert verified_user.admin == old_data['admin']
    assert verified_user.created == old_data['created']


async def test_delete_one(
    admin_user: User,
    admin_user_token: Token,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    data = {
        'uuid': '897f7448-2cdc-4d1d-a726-6adc6dcf40c0',
        'username': 'test',
        'email': 'test@test.com',
        'password': 'test#3C',
    }
    new_user = await create_user(data, async_session)
    resp = await async_client.delete(
        f'users/{new_user.uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    user = await async_session.scalar(sa.select(User).filter_by(uuid=new_user.uuid))
    assert user is None
    resp = await async_client.delete(
        f'users/{admin_user.uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json() == {'detail': 'Attempt to delete admin user'}


@pytest.mark.parametrize('entry_factory, expected', [(5, 5)], indirect=['entry_factory'])
async def test_get_user_entries(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    entry_factory: EntryFactory,
    expected: int,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    async for _ in await entry_factory(verified_user, async_session):
        resp = await async_client.get(
            f'users/{verified_user.uuid}/entries',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['total'] == expected
        resp = await async_client.get(
            f'users/{verified_user.uuid}/entries',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json() == {'detail': 'You are not allowed to perform this operation'}


@pytest.mark.usefixtures('post_list')
async def test_get_user_posts(
    admin_user: User,
    admin_user_token: Token,
    unverified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        f'users/{admin_user.uuid}/posts',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['total'] > 0
    resp = await async_client.get(
        f'users/{admin_user.uuid}/posts',
        headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json() == {'detail': 'Your account is inactive. Please activate your account to proceed.'}


async def test_get_user_socials(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        f'users/{verified_user.uuid}/socials',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['user']['uuid'] == str(verified_user.uuid)
    resp = await async_client.get(
        f'users/{verified_user.uuid}/socials',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_update_user_socials(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.put(
        f'users/{verified_user.uuid}/socials',
        json=SOCIAL_DATA,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = SocialRead(**resp.json())
    await async_session.refresh(verified_user)
    for k, v in SOCIAL_DATA.items():
        assert getattr(resp_data, k) == v
        assert getattr(verified_user.socials, k) == v
    resp = await async_client.put(
        f'users/{verified_user.uuid}/socials',
        json=SOCIAL_DATA,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_patch_user_socials(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    data = {
        'first_name': 'John',
        'last_name': 'Doe',
    }
    resp = await async_client.patch(
        f'users/{verified_user.uuid}/socials',
        json=data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = SocialRead(**resp.json())
    await async_session.refresh(verified_user)
    for k, v in data.items():
        assert getattr(resp_data, k) == v
        assert getattr(verified_user.socials, k) == v
    resp = await async_client.patch(
        f'users/{verified_user.uuid}/socials',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_get_user_avatar(
    verified_user: User,
    verified_user_token: Token,
    unverified_user_token: Token,
    image_factory: ImageFactory[User],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for filename, img_path, _ in await image_factory(instance=verified_user, async_session=async_session):
        resp = await async_client.get(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert verified_user.socials.avatar == filename
        assert Path.exists(img_path)
        resp = await async_client.get(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_update_user_avatar(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for old_filename, old_img_path, _ in await image_factory(instance=verified_user, async_session=async_session):
        img = create_temp_image()
        resp = await async_client.put(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
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
        resp = await async_client.put(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
            files={'file': (img.name, img, 'image/png')},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_delete_user_avatar(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for filename, img_path, _ in await image_factory(instance=verified_user, async_session=async_session):
        assert verified_user.socials.avatar == filename
        resp = await async_client.delete(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        await async_session.refresh(verified_user)
        assert verified_user.socials.avatar == config.DEFAULT_AVATAR
        assert not Path.exists(img_path)
        resp = await async_client.delete(
            f'users/{verified_user.uuid}/socials/avatar',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
