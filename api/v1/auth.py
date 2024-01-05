from fastapi import Depends, APIRouter, HTTPException, status, Header, Response
from fastapi.background import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from api.v1.dependencies import get_current_user
from models.users import User
from repositories.auth import AuthRepository
from repositories.redis import RedisRepository
from schemas.auth import Token, VerifyUserRequest
from schemas.users import UserRead, UserCreate


router = APIRouter(
    prefix='/api/v1/auth',
    tags=['auth'],
)


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=UserRead)
async def register(
    response: Response,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    auth_repo: AuthRepository = Depends(),
) -> UserRead:
    from api import users_router_v1

    user = await auth_repo.register_user(user_data, background_tasks)
    response.headers['Location'] = users_router_v1.url_path_for('get_one', uuid=user.uuid)
    return UserRead.model_validate(user)


@router.post(
    '/confirm',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'The confirmation token is invalid or has expired.'}},
)
async def confirm_account(
    data: VerifyUserRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.activate_user_account(user, data, background_tasks)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'msg': 'Account has been confirmed successfully.'},
        ),
    )


@router.post('/token', response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> Token:
    token, user = await auth_repo.get_token(form_data)
    await redis_repo.send_token(token.refresh_token, user.uuid)
    return token


@router.post(
    '/refresh',
    response_model=Token,
    responses={401: {'description': 'Unauthorized'}},
)
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


@router.post(
    '/revoke',
    response_class=JSONResponse,
    responses={401: {'description': 'Unauthorized'}},
)
async def revoke_refresh_token(
    refresh_token: str = Header(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> JSONResponse:
    user = auth_repo.validate_token(refresh_token, refresh_token=True)
    await redis_repo.delete_token(user.uuid)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'msg': 'refresh token has been successfully revoked'},
        ),
    )
