from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from datetime import datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from fakeredis.aioredis import FakeRedis
from fastapi import status
from freezegun.api import FrozenDateTimeFactory
from httpx import AsyncClient, HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config, fm
from src.models.socials import SocialMedia
from src.models.users import User
from src.repositories.auth import AuthRepository
from src.schemas.auth import Token
from src.schemas.users import UserRead
from tests.utils import (
    ANONYMOUS_USER,
    USER_DATA,
    VERIFIED_USER,
    TokenHandler,
    create_token,
    parse_payload,
)


@pytest.mark.dependency()
async def test_register(async_client: AsyncClient, async_session: AsyncSession) -> None:
    with fm.record_messages() as outbox:
        resp = await async_client.post('auth/register', json=USER_DATA)
        assert resp.status_code == status.HTTP_201_CREATED
        assert len(outbox) == 1
        assert outbox[0]['from'] == f'{config.MAIL_FROM_NAME} <{config.MAIL_FROM}>'
        assert outbox[0]['to'] == USER_DATA['email']
        assert 'Account Activation' in outbox[0]['subject']
        activation_token = parse_payload(outbox)
        assert activation_token is not None
        pytest.ACTIVATION_TOKEN = activation_token
    resp_data = UserRead(**resp.json())
    assert resp_data.confirmed is False
    assert resp_data.confirmed_on is None
    assert resp_data.active is False
    assert resp_data.admin is False
    assert resp_data.username == USER_DATA['username']
    assert resp_data.email == USER_DATA['email']
    assert str(resp_data.uuid) in resp.headers['Location']
    user = await async_session.scalar(sa.select(User).filter_by(uuid=resp_data.uuid))
    assert user is not None
    social = await async_session.scalar(sa.select(SocialMedia).filter_by(user_id=resp_data.uuid))
    assert social is not None


@pytest.mark.dependency(depends=['test_register'])
async def test_token(
    async_client: AsyncClient, async_session: AsyncSession, redis_client: FakeRedis
) -> None:
    data = {'username': USER_DATA['username'], 'password': USER_DATA['password']}
    resp = await async_client.post('auth/token', data=data)
    assert resp.status_code == status.HTTP_200_OK
    resp_data = Token(**resp.json())
    user = await async_session.scalar(sa.select(User).filter_by(username=USER_DATA['username']))
    assert user is not None
    refresh_token_redis = await redis_client.hget(config.REDIS_HASH, str(user.uuid))
    assert refresh_token_redis is not None
    assert resp_data.refresh_token == TokenHandler.decrypt_token(refresh_token_redis)
    pytest.ACCESS_TOKEN = resp_data.access_token
    pytest.REFRESH_TOKEN = resp_data.refresh_token


@pytest.mark.dependency(depends=['test_token'])
async def test_refresh_access_token(async_client: AsyncClient, redis_client: FakeRedis) -> None:
    refresh_token = str(pytest.REFRESH_TOKEN)
    resp = await async_client.post('auth/refresh', headers={'refresh-token': refresh_token})
    assert resp.status_code == status.HTTP_200_OK
    resp_data = Token(**resp.json())
    user_access = AuthRepository.validate_token(resp_data.access_token)
    user_refresh = AuthRepository.validate_token(resp_data.refresh_token, refresh_token=True)
    assert user_access.uuid == user_refresh.uuid
    refresh_token_redis = await redis_client.hget(config.REDIS_HASH, user_refresh.uuid)
    assert refresh_token_redis is not None
    assert refresh_token == TokenHandler.decrypt_token(refresh_token_redis)


@pytest.mark.dependency(depends=['test_token'])
async def test_revoke_refresh_token(async_client: AsyncClient, redis_client: FakeRedis) -> None:
    refresh_token = str(pytest.REFRESH_TOKEN)
    user_refresh = AuthRepository.validate_token(refresh_token, refresh_token=True)
    resp = await async_client.post('auth/revoke', headers={'refresh-token': refresh_token})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'refresh token has been successfully revoked',
    }
    refresh_token_redis = await redis_client.hget(config.REDIS_HASH, user_refresh.uuid)
    assert refresh_token_redis is None


@pytest.mark.dependency(depends=['test_token'])
async def test_resend_activation(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    with fm.record_messages() as outbox:
        resp = await async_client.post(
            'auth/resend-activation', headers={'Authorization': f'Bearer {access_token}'}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(outbox) == 1
        assert outbox[0]['from'] == f'{config.MAIL_FROM_NAME} <{config.MAIL_FROM}>'
        assert outbox[0]['to'] == USER_DATA['email']
        assert 'Account Activation' in outbox[0]['subject']
        activation_token = parse_payload(outbox)
        assert activation_token is not None


@pytest.mark.dependency(depends=['test_token'])
async def test_activate_account(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    data = {'token': str(pytest.ACTIVATION_TOKEN)}
    resp = await async_client.post(
        'auth/activate', json=data, headers={'Authorization': f'Bearer {access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'Account has been confirmed successfully.',
    }


@pytest.mark.dependency(depends=['test_activate_account'])
async def test_forgot_password(async_client: AsyncClient) -> None:
    with fm.record_messages() as outbox:
        resp = await async_client.post('auth/forgot-password', json={'email': USER_DATA['email']})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {
            'code': status.HTTP_200_OK,
            'message': 'A email with password reset link has been sent to you.',
        }
        assert outbox[0]['from'] == f'{config.MAIL_FROM_NAME} <{config.MAIL_FROM}>'
        assert outbox[0]['to'] == USER_DATA['email']
        assert 'Password Reset' in outbox[0]['subject']
        reset_token = parse_payload(outbox)
        assert reset_token is not None
        pytest.RESET_TOKEN = reset_token


@pytest.mark.dependency(depends=['test_forgot_password'])
async def test_reset_password(async_client: AsyncClient, async_session: AsyncSession) -> None:
    data = {
        'token': str(pytest.RESET_TOKEN),
        'email': USER_DATA['email'],
        'password': 'carol#Bar2',
        'confirm_password': 'carol#Bar2',
    }
    user = await async_session.scalar(sa.select(User).filter_by(username=USER_DATA['username']))
    assert user is not None
    old_password = user.hashed_password
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {'code': status.HTTP_200_OK, 'message': 'Your password has been updated.'}
    await async_session.refresh(user)
    user = await async_session.scalar(sa.select(User).filter_by(username=USER_DATA['username']))
    assert user is not None
    assert old_password != user.hashed_password


@pytest.mark.dependency(depends=['test_activate_account'])
async def test_change_email(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    with fm.record_messages() as outbox:
        resp = await async_client.patch(
            'users/me',
            json={'email': 'carol_new@carol.com'},
            headers={'Authorization': f'Bearer {access_token}'},
        )
        assert resp.status_code == status.HTTP_200_OK
        resp_data = UserRead(**resp.json())
        assert resp_data.confirmed is False
        assert resp_data.confirmed_on is None
        assert len(outbox) == 1
        assert outbox[0]['from'] == f'{config.MAIL_FROM_NAME} <{config.MAIL_FROM}>'
        assert outbox[0]['to'] == resp_data.email
        assert 'Email Change' in outbox[0]['subject']
        email_change_token = parse_payload(outbox)
        assert email_change_token is not None
        pytest.EMAIL_CHANGE_TOKEN = email_change_token
        pytest.NEW_EMAIL = resp_data.email


@pytest.mark.dependency(depends=['test_change_email'])
async def test_resend_email_change_confirmation(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    with fm.record_messages() as outbox:
        resp = await async_client.post(
            'auth/resend-confirmation', headers={'Authorization': f'Bearer {access_token}'}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(outbox) == 1
        assert outbox[0]['from'] == f'{config.MAIL_FROM_NAME} <{config.MAIL_FROM}>'
        assert outbox[0]['to'] == str(pytest.NEW_EMAIL)
        assert 'Email Change' in outbox[0]['subject']
        activation_token = parse_payload(outbox)
        assert activation_token is not None


@pytest.mark.dependency(depends=['test_change_email'])
async def test_confirm_email_change(async_client: AsyncClient, async_session: AsyncSession) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    data = {'token': str(pytest.EMAIL_CHANGE_TOKEN)}
    resp = await async_client.post(
        'auth/confirm-change', json=data, headers={'Authorization': f'Bearer {access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'Account has been updated successfully.',
    }
    user = await async_session.scalar(sa.select(User).filter_by(email=str(pytest.NEW_EMAIL)))
    assert user is not None
    assert user.confirmed is True
    assert user.confirmed_on is not None


@pytest.mark.dependency(depends=['test_change_email'])
async def test_register_duplicate(async_client: AsyncClient) -> None:
    data = {
        'username': USER_DATA['username'],
        'email': str(pytest.NEW_EMAIL),
        'password': 'foo#Bar1',
        'confirm_password': 'foo#Bar1',
    }
    resp = await async_client.post('auth/register', json=data)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json() == {
        'detail': 'Please choose a different username\nPlease choose a different email'
    }


@pytest.mark.dependency(depends=['test_reset_password'])
async def test_reset_password_token_does_not_work_twice(async_client: AsyncClient) -> None:
    data = {
        'token': str(pytest.RESET_TOKEN),
        'email': USER_DATA['email'],
        'password': 'carol#Bar2',
        'confirm_password': 'carol#Bar2',
    }
    resp = await async_client.put('auth/reset-password', json=data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


@pytest.mark.dependency(depends=['test_change_email'])
async def test_change_email_with_old_token(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    resp = await async_client.patch(
        'users/me',
        json={'email': 'carol_new2@carol.com'},
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = UserRead(**resp.json())
    assert resp_data.confirmed is False
    assert resp_data.confirmed_on is None
    data = {'token': str(pytest.EMAIL_CHANGE_TOKEN)}
    resp = await async_client.post(
        'auth/confirm-change', json=data, headers={'Authorization': f'Bearer {access_token}'}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


@pytest.mark.dependency(depends=['test_forgot_password'])
async def test_change_email_with_reset_password_token(async_client: AsyncClient) -> None:
    access_token = str(pytest.ACCESS_TOKEN)
    data = {'token': str(pytest.RESET_TOKEN)}
    resp = await async_client.post(
        'auth/confirm-change', json=data, headers={'Authorization': f'Bearer {access_token}'}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'The confirmation link is invalid or has expired.'}


@pytest.mark.parametrize(
    'username, email, password, expectation',
    [
        ('user1', 'user1@user.com', 'foo#Bar34', does_not_raise()),
        ('user2', 'user2@user.com', 'foo#Ba3', pytest.raises(HTTPStatusError)),
        ('user3', 'user3@user.com', '123456789', pytest.raises(HTTPStatusError)),
        ('user4', 'user4@user.com', '', pytest.raises(HTTPStatusError)),
        ('user5', 'user5@user.com', 'foo#Bar34', does_not_raise()),
        ('user._5', 'user6@user.com', 'foo#Bar34', does_not_raise()),
        ('_user', 'user7@user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('.user', 'user8@user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('5user', 'user6@user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('_user#', 'user7@user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('', 'user8@user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('user9', 'user9user.com', 'foo#Bar34', pytest.raises(HTTPStatusError)),
        ('user10', 'user10@firemailbox.club', 'foo#Bar34', pytest.raises(HTTPStatusError)),
    ],
)
async def test_register_with_different_creds(
    async_client: AsyncClient,
    username: str,
    email: str,
    password: str,
    expectation: AbstractContextManager[Any],
) -> None:
    with expectation:
        data = {
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': password,
        }
        resp = await async_client.post('auth/register', json=data)
        resp.raise_for_status()


async def test_refresh_access_token_anonymous(
    anonymous_user_token: str, async_client: AsyncClient
) -> None:
    resp = await async_client.post('auth/refresh', headers={'refresh-token': anonymous_user_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_access_token_no_redis(
    verified_user: User,
    verified_user_token: Token,
    async_client: AsyncClient,
    redis_client: FakeRedis,
) -> None:
    await redis_client.hdel(config.REDIS_HASH, verified_user.uuid)
    resp = await async_client.post(
        'auth/refresh', headers={'refresh-token': verified_user_token.refresh_token}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_revoke_refresh_token_anonymous(
    anonymous_user_token: str, async_client: AsyncClient
) -> None:
    resp = await async_client.post('auth/revoke', headers={'refresh-token': anonymous_user_token})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_resend_activation_verified_user(
    verified_user_token: Token, async_client: AsyncClient
) -> None:
    resp = await async_client.post(
        'auth/resend-activation',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Account already activated.'}


async def test_resend_activation_unverified_user(
    unverified_user_token: Token, async_client: AsyncClient
) -> None:
    resp = await async_client.post(
        'auth/resend-activation',
        headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'New confirmation email has been sent.',
    }


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


async def test_reset_password_unverified_user(
    unverified_user: User, async_client: AsyncClient
) -> None:
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
    assert resp.json() == {
        'detail': 'Your account is inactive. Please activate your account to proceed.'
    }


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


async def test_refresh_access_token_with_expired_token(
    verified_user_token: Token, async_client: AsyncClient, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime.now() + timedelta(seconds=config.JWT_REFRESH_EXPIRATION + 1))
    resp = await async_client.post(
        'auth/refresh', headers={'refresh-token': verified_user_token.refresh_token}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json() == {'detail': 'Invalid refresh token'}


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
