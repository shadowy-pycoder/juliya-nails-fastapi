from fastapi import Depends, APIRouter, HTTPException, status, Header, Response
from fastapi.background import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from api.v1.dependencies import get_current_user, check_disposable
from models.users import User
from repositories.auth import AuthRepository
from repositories.redis import RedisRepository
from schemas.auth import Token, VerifyUserRequest, EmailRequest, ResetRequest
from schemas.users import UserRead, UserCreate
from utils import AccountAction


router = APIRouter(
    prefix='/api/v1/auth',
    tags=['auth'],
)


@router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
    response_model=UserRead,
    responses={400: {'description': 'Disposable domains are not allowed'}},
)
async def register(
    response: Response,
    background_tasks: BackgroundTasks,
    auth_repo: AuthRepository = Depends(),
    user_data: UserCreate = Depends(check_disposable),
) -> UserRead:
    from api import users_router_v1

    user = await auth_repo.register_user(user_data, background_tasks)
    response.headers['Location'] = users_router_v1.url_path_for('get_one', uuid=user.uuid)
    return UserRead.model_validate(user)


@router.post(
    '/resend-activation',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'Account already confirmed.'}},
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'New confirmation email has been sent.'},
        ),
    )


@router.post(
    '/resend-confirmation',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'Account already confirmed.'}},
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'New confirmation email has been sent.'},
        ),
    )


@router.post(
    '/activate',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'The confirmation token is invalid or has expired.'}},
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'Account has been confirmed successfully.'},
        ),
    )


@router.post(
    '/confirm-change',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'The confirmation token is invalid or has expired.'}},
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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'Account has been updated successfully.'},
        ),
    )


@router.post(
    '/forgot-password',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'Disposable domains are not allowed'}},
)
async def forgot_password(
    background_tasks: BackgroundTasks,
    auth_repo: AuthRepository = Depends(),
    user_data: EmailRequest = Depends(check_disposable),
) -> JSONResponse:
    await auth_repo.email_forgot_password_link(
        user_data,
        background_tasks,
        context=AccountAction.RESET_PASSWORD,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'A email with password reset link has been sent to you.'},
        ),
    )


@router.put(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={400: {'description': 'The confirmation token is invalid or has expired.'}},
)
async def reset_password(
    auth_repo: AuthRepository = Depends(),
    data: ResetRequest = Depends(check_disposable),
) -> JSONResponse:
    await auth_repo.reset_user_password(data)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {'code': 200, 'message': 'Your password has been updated.'},
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
            detail='Invalid refresh token.',
            headers={'WWW-Authenticate': 'Bearer'},
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
            {'message': 'refresh token has been successfully revoked'},
        ),
    )
