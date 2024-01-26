from datetime import datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.users import User
from src.schemas.auth import Token
from src.schemas.entries import EntryRead
from tests.utils import EntryFactory, EntryList


@pytest.mark.parametrize('entry_list', [{'days': 1, 'offset': 0}], indirect=True)
async def test_create_one(
    verified_user_token: Token,
    unverified_user_token: Token,
    entry_list: EntryList,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        'entries',
        json=entry_list[0],
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp_data = EntryRead(**resp.json())
    assert str(resp_data.uuid) in resp.headers['Location']
    assert (
        datetime.combine(resp_data.date, resp_data.time).timestamp()
        + timedelta(minutes=resp_data.duration).total_seconds()
        == resp_data.ending_time
    )
    resp = await async_client.post(
        'entries',
        json=entry_list[0],
        headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('entry_list', [{'days': 2, 'offset': 0}], indirect=True)
async def test_create_one_no_conflict(
    admin_user_token: Token,
    verified_user_token: Token,
    entry_list: EntryList,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        'entries',
        json=entry_list[0],
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp = await async_client.post(
        'entries',
        json=entry_list[1],
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp = await async_client.post(
        'entries',
        json=entry_list[2],
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize('entry_list', [{'days': 3, 'offset': 1}], indirect=True)
async def test_create_one_conflict(
    admin_user_token: Token,
    verified_user_token: Token,
    entry_list: EntryList,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        'entries',
        json=entry_list[0],
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp = await async_client.post(
        'entries',
        json=entry_list[1],
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert entry_list[3].date().isoformat() in resp.json()['detail']
    resp = await async_client.post(
        'entries',
        json=entry_list[2],
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert entry_list[3].date().isoformat() in resp.json()['detail']


@pytest.mark.parametrize('entry_factory', [5], indirect=True)
async def test_get_all(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    entry_factory: EntryFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for _ in await entry_factory(admin_user, async_session):
        resp = await async_client.get(
            'entries', headers={'Authorization': f'Bearer {admin_user_token.access_token}'}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['total'] > 0
        resp = await async_client.get(
            'entries', headers={'Authorization': f'Bearer {verified_user_token.access_token}'}
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_get_by_date(
    verified_user_token: Token,
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        f'entries/date/{datetime.now().date().isoformat()}',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.parametrize('entry_factory', [5], indirect=True)
async def test_get_one(
    verified_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    second_verified_user_token: Token,
    entry_factory: EntryFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for entries in await entry_factory(verified_user, async_session):
        entry = entries[0]

        resp = await async_client.get(
            f'entries/{entry.uuid}',
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['uuid'] == str(entry.uuid)
        resp = await async_client.get(
            f'entries/{entry.uuid}',
            headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        resp = await async_client.get(
            f'entries/{entry.uuid}',
            headers={'Authorization': f'Bearer {second_verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('entry_factory', [1], indirect=True)
async def test_update_one(
    verified_user: User,
    verified_user_token: Token,
    second_verified_user_token: Token,
    entry_factory: EntryFactory,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    async for entries in await entry_factory(verified_user, async_session):
        entry = entries[0]
        date = datetime.now() + timedelta(days=1)
        data = {
            'date': date.date().isoformat(),
            'time': date.time().isoformat(),
            'services': [],
        }
        resp = await async_client.put(
            f'entries/{entry.uuid}',
            json=data,
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['uuid'] == str(entry.uuid)
        await async_session.refresh(entry)
        assert entry.date.isoformat() == data['date']
        assert entry.time.isoformat() == data['time']
        assert entry.services == []
        resp = await async_client.put(
            f'entries/{entry.uuid}',
            json=data,
            headers={'Authorization': f'Bearer {second_verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
