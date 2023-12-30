from typing import TypeAlias

from fastapi import status, Depends, HTTPException
from pydantic import UUID4

from models.users import User
from schemas.users import UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserRead
from services.auth import get_current_user
from services.users import UserService


UserSchema: TypeAlias = UserCreate | UserUpdate | UserUpdatePartial | UserAdminUpdate | UserAdminUpdatePartial


def get_admin_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this operation')
    return user


async def verify_credentials(uuid: UUID4 | str, credentials: UserSchema, service: UserService) -> User:
    user = await service.find_by_uuid(uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User does not exist')
    errors = []
    username_err = await service.verify_username(credentials.username) if credentials.username else ''
    if username_err and credentials.username != user.username:
        errors.append(username_err)
    email_err = await service.verify_email(credentials.email) if credentials.email else ''
    if email_err and credentials.email != user.email:
        errors.append(email_err)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='\n'.join(e for e in errors))
    return user