from fastapi import Depends, APIRouter, HTTPException, status, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from services.auth import AuthService
from services.users import UserService
from services.redis import RedisService
from schemas.auth import Token
from schemas.users import UserRead, UserCreate


router = APIRouter(
    prefix='/api/v1/auth',
    tags=['auth'],
)


@router.post('/register', response_model=UserRead, response_model_exclude_defaults=True)
async def register(
    user_data: UserCreate, auth_service: AuthService = Depends(), user_service: UserService = Depends()
) -> UserRead:
    errors = []
    if username_err := await user_service.verify_username(user_data.username):
        errors.append(username_err)
    if email_err := await user_service.verify_email(user_data.email):
        errors.append(email_err)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='\n'.join(e for e in errors))
    return await auth_service.register_user(user_data)


@router.post('/token', response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(),
    redis_service: RedisService = Depends(),
) -> Token:
    token, user = await auth_service.get_token(form_data)
    await redis_service.send_token(token.refresh_token, user.uuid)
    return token


@router.post("/refresh", response_model=Token, responses={401: {'description': 'Unauthorized'}})
async def refresh_access_token(
    refresh_token: str = Header(),
    auth_service: AuthService = Depends(),
    redis_service: RedisService = Depends(),
) -> Token:
    token, user = await auth_service.get_refresh_token(token=refresh_token)
    redis_token = await redis_service.get_token(user.uuid)
    if not redis_token or token.refresh_token != redis_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post("/revoke", responses={401: {'description': 'Unauthorized'}}, response_class=JSONResponse)
async def revoke_refresh_token(
    refresh_token: str = Header(),
    auth_service: AuthService = Depends(),
    redis_service: RedisService = Depends(),
) -> JSONResponse:
    user = auth_service.validate_token(refresh_token, refresh_token=True)
    await redis_service.delete_token(user.uuid)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder({'OK': 'refresh token has been successfully revoked'})
    )
