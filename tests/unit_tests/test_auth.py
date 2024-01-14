from typing import Any

from cryptography.fernet import Fernet
from fakeredis.aioredis import FakeRedis
from fastapi import status
from httpx import AsyncClient
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config, fm
from src.models.socials import SocialMedia
from src.models.users import User
from src.repositories.auth import AuthRepository
from src.schemas.auth import Token
from src.schemas.users import UserRead

USER_DATA = {
    'username': 'carol',
    'email': 'carol@carol.com',
    'password': 'carol#3C',
    'confirm_password': 'carol#3C',
}


def parse_payload(payload: list[Any]) -> str | None:
    msg_split: list[bytes] = payload[0]._payload[0].get_payload(decode=True).split(b'/')
    for msg in msg_split:
        if msg.startswith(b'eyJ'):
            return msg.split(b'"')[0].decode('utf-8')
    return None


class TokenHandler:
    fernet = Fernet(config.SECRET_KEY)

    @classmethod
    def encrypt_token(cls, token: str) -> bytes:
        return cls.fernet.encrypt(token.encode('utf-8'))

    @classmethod
    def decrypt_token(cls, token: bytes) -> str:
        return cls.fernet.decrypt(token).decode('utf-8')


@pytest.mark.dependency()
async def test_register(async_client: AsyncClient, async_session: AsyncSession) -> None:
    with fm.record_messages() as outbox:
        resp = await async_client.post('auth/register', json=USER_DATA)
        assert resp.status_code == status.HTTP_201_CREATED
        assert len(outbox) == 1
        assert outbox[0]['from'] == f'{config.APP_NAME} <{config.MAIL_FROM}>'
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
        assert outbox[0]['from'] == f'{config.APP_NAME} <{config.MAIL_FROM}>'
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
        assert outbox[0]['from'] == f'{config.APP_NAME} <{config.MAIL_FROM}>'
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
        assert outbox[0]['from'] == f'{config.APP_NAME} <{config.MAIL_FROM}>'
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
        assert outbox[0]['from'] == f'{config.APP_NAME} <{config.MAIL_FROM}>'
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
