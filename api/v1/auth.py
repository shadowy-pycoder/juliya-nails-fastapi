from fastapi import Depends, APIRouter, HTTPException, status, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from repositories.auth import AuthRepository
from repositories.redis import RedisRepository
from repositories.socials import SocialRepository
from schemas.auth import Token
from schemas.socials import SocialCreate
from schemas.users import UserRead, UserCreate


router = APIRouter(
    prefix='/api/v1/auth',
    tags=['auth'],
)


@router.post('/register', response_model=UserRead, response_model_exclude_defaults=True)
async def register(
    user_data: UserCreate,
    auth_repo: AuthRepository = Depends(),
    social_repo: SocialRepository = Depends(),
) -> UserRead:
    user = await auth_repo.register_user(user_data)
    await social_repo.create(SocialCreate(user_id=user.uuid))
    return UserRead.model_validate(user)


@router.post('/token', response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> Token:
    token, user = await auth_repo.get_token(form_data)
    await redis_repo.send_token(token.refresh_token, user.uuid)
    return token


@router.post("/refresh", response_model=Token, responses={401: {'description': 'Unauthorized'}})
async def refresh_access_token(
    refresh_token: str = Header(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> Token:
    token, user = await auth_repo.get_refresh_token(token=refresh_token)
    redis_token = await redis_repo.get_token(user.uuid)
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
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> JSONResponse:
    user = auth_repo.validate_token(refresh_token, refresh_token=True)
    await redis_repo.delete_token(user.uuid)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder({'OK': 'refresh token has been successfully revoked'})
    )
