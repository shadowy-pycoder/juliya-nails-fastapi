from fastapi import status, Depends, HTTPException
from pydantic import UUID4

from models.entries import Entry
from models.users import User
from repositories.auth import oauth2_scheme, AuthRepository
from repositories.entries import EntryRepository
from repositories.users import UserRepository
from schemas.users import UserRead
from utils import HTTP_403_FORBIDDEN


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(),
) -> User:
    user_payload = AuthRepository.validate_token(token)
    return await repo.find_by_uuid(user_payload.uuid)


async def get_admin_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.admin:
        raise HTTP_403_FORBIDDEN
    return user


async def get_active_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Your account is inactive. Please activate your account to proceed.',
        )
    return user


async def get_confirmed_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Please confirm your account to proceed')
    return user


async def validate_entry(
    uuid: UUID4 | str,
    repo: EntryRepository = Depends(),
    user: User = Depends(get_current_user),
) -> Entry:
    entry = await repo.find_by_uuid(uuid, detail='Entry does not exist')
    if not user.admin:
        if entry.user != user or entry.completed:
            raise HTTP_403_FORBIDDEN
    return entry
