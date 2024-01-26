import pytest
import sqlalchemy as sa
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.services import Service
from src.models.users import User
from src.schemas.auth import Token
from src.schemas.services import ServiceRead
from tests.utils import SERVICES, EntryFactory


async def test_create_one(
    admin_user_token: Token,
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    data = {'name': 'test service', 'duration': 30}
    resp = await async_client.post(
        'services',
        json=data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp_data = ServiceRead(**resp.json())
    assert str(resp_data.uuid) in resp.headers['Location']
    assert resp_data.name.lower() == data['name']
    assert resp_data.duration == data['duration']
    resp = await async_client.post(
        'services',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.usefixtures('service_list')
async def test_get_all(
    admin_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        'services', headers={'Authorization': f'Bearer {admin_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['total'] > 0


async def test_get_one(
    admin_user_token: Token,
    service_list: list[Service],
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        f'services/{service_list[0].uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['uuid'] == str(service_list[0].uuid)


@pytest.mark.parametrize('entry_factory, expected', [(5, 5)], indirect=['entry_factory'])
async def test_get_service_entries(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    entry_factory: EntryFactory,
    expected: int,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for _ in await entry_factory(admin_user, async_session):
        resp = await async_client.get(
            f'services/{SERVICES[-1]["uuid"]}/entries',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['total'] == expected
        resp = await async_client.get(
            f'services/{SERVICES[-1]["uuid"]}/entries',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_update_one(
    admin_user_token: Token,
    verified_user_token: Token,
    service_list: list[Service],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    service = service_list[0]
    data = {'name': 'test', 'duration': 15}
    resp = await async_client.put(
        f'services/{service.uuid}',
        json=data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    await async_session.refresh(service)
    assert resp.json()['uuid'] == str(service.uuid)
    assert service.name.lower() == data['name']
    assert service.duration == data['duration']
    assert len(list(await async_session.scalars(service.entries.select()))) == 0
    resp = await async_client.put(
        f'services/{service.uuid}',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('entry_factory', [5], indirect=True)
async def test_patch_one(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    entry_factory: EntryFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for _ in await entry_factory(admin_user, async_session):
        service = (
            await async_session.execute(sa.select(Service).filter_by(uuid=SERVICES[-1]['uuid']))
        ).scalar_one()
        old_name = service.name
        old_entries = await async_session.scalars(service.entries.select())
        data = {'duration': 15}
        resp = await async_client.patch(
            f'services/{service.uuid}',
            json=data,
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        await async_session.refresh(service)
        assert resp.json()['uuid'] == str(service.uuid)
        assert service.name == old_name
        assert service.duration == data['duration']
        result = await async_session.scalars(service.entries.select())
        assert len(list(result.unique())) == len(list(old_entries.unique()))
        resp = await async_client.patch(
            f'services/{service.uuid}',
            json=data,
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_one(
    admin_user_token: Token,
    verified_user_token: Token,
    service_list: list[Service],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    service = service_list[0]
    resp = await async_client.delete(
        f'services/{service.uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    result = await async_session.scalar(sa.select(Service).filter_by(uuid=service.uuid))
    assert result is None
    resp = await async_client.delete(
        f'services/{service.uuid}',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
