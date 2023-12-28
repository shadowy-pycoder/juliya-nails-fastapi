from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import UUID4

from api.v1.dependencies import get_admin_user, verify_credentials
from schemas.users import UserRead, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial
from services.auth import get_current_user
from services.users import UserService


router = APIRouter(
    prefix='/users',
    tags=['users'],
    dependencies=[Depends(get_current_user)],
    responses={404: {'description': 'Not found'}, 401: {'description': 'Unauthorized'}},
)


@router.get('/', response_model=list[UserRead])
async def get_users(service: UserService = Depends()) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in await service.find_all()]


@router.get('/me', response_model=UserRead)
async def get_me(user: UserRead = Depends(get_current_user)) -> UserRead:
    return user


@router.put('/me', response_model=UserRead)
async def update_me(
    user_data: UserUpdate, current_user: UserRead = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    user = await verify_credentials(current_user.uuid, user_data, service)
    result = await service.update(user, user_data)
    return UserRead.model_validate(result)


@router.patch('/me', response_model=UserRead)
async def patch_me(
    user_data: UserUpdatePartial, current_user: UserRead = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    user = await verify_credentials(current_user.uuid, user_data, service)
    result = await service.update(user, user_data, partial=True)
    return UserRead.model_validate(result)


@router.get('/{uuid}', response_model=UserRead)
async def get_one(uuid: UUID4, service: UserService = Depends()) -> UserRead:
    user = await service.find_by_uuid(uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User does not exist')
    return UserRead.model_validate(user)


@router.put(
    '/{uuid}',
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
)
async def update_one(uuid: UUID4, user_data: UserAdminUpdate, service: UserService = Depends()) -> UserRead:
    user = await verify_credentials(uuid, user_data, service)
    result = await service.update(user, user_data)
    return UserRead.model_validate(result)


@router.patch(
    '/{uuid}',
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
)
async def patch_one(uuid: UUID4, user_data: UserAdminUpdatePartial, service: UserService = Depends()) -> UserRead:
    user = await verify_credentials(uuid, user_data, service)
    result = await service.update(user, user_data, partial=True)
    return UserRead.model_validate(result)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4, service: UserService = Depends()) -> None:
    user = await service.find_by_uuid(uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User does not exist')
    if user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Attempt to delete admin user')
    await service.delete(user)
