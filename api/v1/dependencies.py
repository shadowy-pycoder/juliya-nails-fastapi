from typing import TypeAlias

from fastapi import status, Depends, HTTPException

from models.users import User
from schemas.users import UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserRead
from services.auth import oauth2_scheme, AuthService
from services.users import UserService


UserSchema: TypeAlias = UserCreate | UserUpdate | UserUpdatePartial | UserAdminUpdate | UserAdminUpdatePartial


async def get_current_user(token: str = Depends(oauth2_scheme), service: UserService = Depends()) -> User:
    user_payload = AuthService.validate_token(token)
    return await service.find_by_uuid(user_payload.uuid)


def get_admin_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this operation')
    return user


def get_active_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Your account is inactive. Please contact support')
    return user


async def verify_credentials(user: User, credentials: UserSchema, service: UserService) -> None:
    errors = []
    if credentials.username and credentials.username != user.username:
        if username_err := await service.verify_username(credentials.username):
            errors.append(username_err)
    if credentials.email and credentials.email != user.email:
        if email_err := await service.verify_email(credentials.email):
            errors.append(email_err)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='\n'.join(e for e in errors))
