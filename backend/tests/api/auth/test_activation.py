from fastapi import status
from httpx import AsyncClient
from src.schemas.auth import Token


async def test_resend_activation_verified_user(verified_user_token: Token, async_client: AsyncClient) -> None:
    resp = await async_client.post(
        'auth/resend-activation',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json() == {'detail': 'Account already activated.'}


async def test_resend_activation_unverified_user(unverified_user_token: Token, async_client: AsyncClient) -> None:
    resp = await async_client.post(
        'auth/resend-activation',
        headers={'Authorization': f'Bearer {unverified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        'code': status.HTTP_200_OK,
        'message': 'New confirmation email has been sent.',
    }
