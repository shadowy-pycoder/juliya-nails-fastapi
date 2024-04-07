from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.background import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.logger import logger
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.api.v1.dependencies import check_disposable, get_current_user
from src.models.users import User
from src.repositories.auth import AuthRepository
from src.repositories.redis import RedisRepository
from src.schemas.auth import EmailRequest, ResetRequest, Token, VerifyUserRequest
from src.schemas.users import UserCreate, UserRead
from src.utils import AccountAction


router = APIRouter(
    prefix='/v1/auth',
    tags=['auth'],
)


@router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_disposable)],
    response_model=UserRead,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'Disposable domains are not allowed'}},
)
async def register(
    response: Response,
    background_tasks: BackgroundTasks,
    user_data: UserCreate,
    auth_repo: AuthRepository = Depends(),
) -> UserRead:
    from src.api import users_router_v1

    user = await auth_repo.register_user(user_data, background_tasks)
    response.headers['Location'] = users_router_v1.url_path_for('get_one', uuid=user.uuid)
    logger.info(f'[registration]: {user}')
    return UserRead.model_validate(user)


@router.post(
    '/resend-activation',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'Account already confirmed.'}},
)
async def resend_activation(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.resend_confirmation(
        user,
        background_tasks,
        context=AccountAction.ACTIVATE,
    )
    logger.info(f'[resend activation]: {user}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'New confirmation email has been sent.'},
        ),
    )


@router.post(
    '/resend-confirmation',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'Account already confirmed.'}},
)
async def resend_email_change_confirmation(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.resend_confirmation(
        user,
        background_tasks,
        context=AccountAction.CHANGE_EMAIL,
    )
    logger.info(f'[resend confirmation]: {user}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'New confirmation email has been sent.'},
        ),
    )


@router.post(
    '/activate',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'The confirmation token is invalid or has expired.'}},
)
async def activate_account(
    data: VerifyUserRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.activate_user_account(
        user,
        data,
        background_tasks,
        context=AccountAction.ACTIVATE,
    )
    logger.info(f'[account activation]: {user}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'Account has been confirmed successfully.'},
        ),
    )


@router.post(
    '/confirm-change',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'The confirmation token is invalid or has expired.'}},
)
async def confirm_email_change(
    data: VerifyUserRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.activate_user_account(
        user,
        data,
        background_tasks,
        context=AccountAction.CHANGE_EMAIL,
    )
    logger.info(f'[email change]: {user}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'Account has been updated successfully.'},
        ),
    )


@router.post(
    '/forgot-password',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_disposable)],
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'Disposable domains are not allowed'}},
)
async def forgot_password(
    user_data: EmailRequest,
    background_tasks: BackgroundTasks,
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.email_forgot_password_link(
        user_data,
        background_tasks,
        context=AccountAction.RESET_PASSWORD,
    )
    logger.info(f'[forgot password]: {user_data.email}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                'code': status.HTTP_200_OK,
                'message': 'A email with password reset link has been sent to you.',
            },
        ),
    )


@router.put(
    '/reset-password',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_disposable)],
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'The confirmation token is invalid or has expired.'}},
)
async def reset_password(
    user_data: ResetRequest,
    auth_repo: AuthRepository = Depends(),
) -> JSONResponse:
    await auth_repo.reset_user_password(user_data)
    logger.info(f'[reset password]: {user_data.email}')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'Your password has been updated.'},
        ),
    )


@router.post('/token', status_code=status.HTTP_200_OK, response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> Token:
    token, user = await auth_repo.get_token(form_data)
    logger.info(f'[access token]: {user}')
    await redis_repo.send_token(token.refresh_token, user.uuid)
    logger.info(f'[redis]: refresh token for uuid="{user.uuid}" sent')
    return token


@router.post(
    '/refresh',
    status_code=status.HTTP_200_OK,
    response_model=Token,
    responses={status.HTTP_401_UNAUTHORIZED: {'description': 'Unauthorized'}},
)
async def refresh_access_token(
    refresh_token: str = Header(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> Token:
    token, user = await auth_repo.get_refresh_token(token=refresh_token)
    logger.info(f'[refresh access token]: {user}')
    redis_token = await redis_repo.get_token(user.uuid)
    logger.info(f'[redis]: refresh token for uuid="{user.uuid}" retrieved')
    if not redis_token or token.refresh_token != redis_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return token


@router.post(
    '/revoke',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={status.HTTP_400_BAD_REQUEST: {'description': 'Unauthorized'}},
)
async def revoke_refresh_token(
    refresh_token: str = Header(),
    auth_repo: AuthRepository = Depends(),
    redis_repo: RedisRepository = Depends(),
) -> JSONResponse:
    user = auth_repo.validate_token(refresh_token, refresh_token=True)
    logger.info(f'[revoke access token]: {user}')
    await redis_repo.delete_token(user.uuid)
    logger.info(f'[redis]: refresh token for uuid="{user.uuid}" deleted')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': status.HTTP_200_OK, 'message': 'refresh token has been successfully revoked'},
        ),
    )
