import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.users import User
from src.schemas.auth import Token
from src.schemas.socials import SocialRead
from tests.utils import SOCIAL_DATA, ImageFactory


@pytest.mark.usefixtures('admin_user', 'verified_user', 'unverified_user', 'inactive_user')
async def test_get_all(
    admin_user_token: Token,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get('socials', headers={'Authorization': f'Bearer {admin_user_token.access_token}'})
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()['items']) > 0
    resp = await async_client.get('socials', headers={'Authorization': f'Bearer {verified_user_token.access_token}'})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_get_one(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for _ in await image_factory(instance=verified_user, async_session=async_session):
        resp = await async_client.get(
            f'socials/{verified_user.socials.uuid}',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        await async_session.refresh(verified_user)
        assert resp.status_code == status.HTTP_200_OK
        assert str(verified_user.socials.uuid) == resp.json()['uuid']
        resp = await async_client.get(
            f'socials/{verified_user.socials.uuid}',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_update_one(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    async for _ in await image_factory(instance=verified_user, async_session=async_session):
        resp = await async_client.put(
            f'socials/{verified_user.socials.uuid}',
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
            f'socials/{verified_user.socials.uuid}',
            json=SOCIAL_DATA,
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_patch_one(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    async for _ in await image_factory(instance=verified_user, async_session=async_session):
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
        }
        resp = await async_client.patch(
            f'socials/{verified_user.socials.uuid}',
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
            f'socials/{verified_user.socials.uuid}',
            json=data,
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', ['profiles'], indirect=True)
async def test_delete_one(
    admin_user_token: Token,
    verified_user: User,
    verified_user_token: Token,
    image_factory: ImageFactory[User],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for _ in await image_factory(instance=verified_user, async_session=async_session):
        resp = await async_client.delete(
            f'socials/{verified_user.socials.uuid}',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        resp = await async_client.delete(
            f'socials/{verified_user.socials.uuid}',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        await async_session.refresh(verified_user)
        assert verified_user.socials is None
