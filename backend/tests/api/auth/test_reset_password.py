from datetime import datetime, timedelta

from fastapi import status
from freezegun.api import FrozenDateTimeFactory
from httpx import AsyncClient

from src.core.config import config, fm
from src.models.users import User
from tests.utils import ANONYMOUS_USER, parse_payload


async def test_forgot_password_non_existing_email(async_client: AsyncClient) -> None:
    resp = await async_client.post('auth/forgot-password', json={'email': ANONYMOUS_USER['email']})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'A email with password reset link has been sent to you.',
    }


async def test_reset_password_admin_user(admin_user: User, async_client: AsyncClient) -> None:
    data = {
        'token': 'token',
        'email': admin_user.email,
        'password': 'passWord1#23',
        'confirm_password': 'passWord1#23',
    }
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


async def test_reset_password_unverified_user(unverified_user: User, async_client: AsyncClient) -> None:
    data = {
        'token': 'token',
        'email': unverified_user.email,
        'password': 'passWord1#23',
        'confirm_password': 'passWord1#23',
    }
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {
        'detail': 'Your account is not verified. Please check your email inbox to verify your account.'
    }


async def test_reset_password_inactive_user(inactive_user: User, async_client: AsyncClient) -> None:
    data = {
        'token': 'token',
        'email': inactive_user.email,
        'password': 'passWord1#23',
        'confirm_password': 'passWord1#23',
    }
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Your account is inactive. Please activate your account to proceed.'}


async def test_reset_password_anonymous_user(async_client: AsyncClient) -> None:
    data = {
        'token': 'token',
        'email': ANONYMOUS_USER['email'],
        'password': 'passWord1#23',
        'confirm_password': 'passWord1#23',
    }
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


async def test_reset_password_with_expired_confirm_token(
    verified_user: User, async_client: AsyncClient, freezer: FrozenDateTimeFactory
) -> None:
    with fm.record_messages() as outbox:
        now = datetime.now()
        resp = await async_client.post('auth/forgot-password', json={'email': verified_user.email})
        assert resp.status_code == status.HTTP_200_OK
        reset_token = parse_payload(outbox)
        assert reset_token is not None
        freezer.move_to(now + timedelta(seconds=config.CONFIRM_EXPIRATION + 1))
        data = {
            'token': reset_token,
            'email': verified_user.email,
            'password': 'alice#Bar2',
            'confirm_password': 'alice#Bar2',
        }
        resp = await async_client.put('auth/reset-password', json=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


async def test_reset_password_with_different_email(
    verified_user: User, admin_user: User, async_client: AsyncClient
) -> None:
    with fm.record_messages() as outbox:
        resp = await async_client.post('auth/forgot-password', json={'email': admin_user.email})
        assert resp.status_code == status.HTTP_200_OK
        reset_token = parse_payload(outbox)
        assert reset_token is not None
        data = {
            'token': reset_token,
            'email': verified_user.email,
            'password': 'alice#Bar2',
            'confirm_password': 'alice#Bar2',
        }
        resp = await async_client.put('auth/reset-password', json=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}
