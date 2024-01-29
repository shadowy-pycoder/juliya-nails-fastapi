from datetime import datetime, timedelta

from fastapi import status
from freezegun.api import FrozenDateTimeFactory
from httpx import AsyncClient

from src.core.config import config, fm
from src.models.users import User
from src.schemas.auth import Token
from tests.utils import VERIFIED_USER, create_token, parse_payload


async def test_change_email_with_expired_access_token(
    verified_user_token: Token, async_client: AsyncClient, freezer: FrozenDateTimeFactory
) -> None:
    now = datetime.now()
    data = {'token': 'token'}
    freezer.move_to(now + timedelta(seconds=config.JWT_EXPIRATION + 1))
    resp = await async_client.post(
        'auth/confirm-change',
        json=data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json() == {'detail': 'Could not validate credentials'}


async def test_change_email_with_different_access_token(
    verified_user_token: Token, unverified_user_token: Token, async_client: AsyncClient
) -> None:
    with fm.record_messages() as outbox:
        resp = await async_client.patch(
            'users/me',
            json={'email': 'alice_new@alice.com'},
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        email_change_token = parse_payload(outbox)
        assert email_change_token is not None
        data = {'token': email_change_token}
        resp = await async_client.post(
            'auth/confirm-change',
            json=data,
            headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


async def test_resend_email_change_confirmation_verified_user(
    verified_user_token: Token, async_client: AsyncClient
) -> None:
    resp = await async_client.post(
        'auth/resend-confirmation',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Account already confirmed.'}


async def test_resend_email_change_confirmation_unverified_user(
    unverified_user_token: Token, async_client: AsyncClient
) -> None:
    resp = await async_client.post(
        'auth/resend-confirmation',
        headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Please activate your account to proceed.'}


async def test_resend_email_change_confirmation_inactive_user(
    inactive_user_token: Token, async_client: AsyncClient
) -> None:
    resp = await async_client.post(
        'auth/resend-confirmation',
        headers={'Authorization': f'Bearer {inactive_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Account already confirmed.'}


async def test_change_email_with_expired_confirm_token(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    with fm.record_messages() as outbox:
        now = datetime.now()
        resp = await async_client.patch(
            'users/me',
            json={'email': 'alice_new@alice.com'},
            headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        email_change_token = parse_payload(outbox)
        assert email_change_token is not None
        freezer.move_to(now + timedelta(seconds=config.CONFIRM_EXPIRATION + 1))
        data = {'token': email_change_token}
        new_token = await create_token(verified_user, VERIFIED_USER, async_client)
        resp = await async_client.post(
            'auth/confirm-change',
            json=data,
            headers={'Authorization': f'Bearer {new_token.access_token}'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}
