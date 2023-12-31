from fastapi import APIRouter, status, Depends, HTTPException
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user, verify_credentials
from schemas.socials import SocialRead, SocialAdminUpdate, SocialAdminUpdatePartial
from schemas.users import UserRead, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter
from services.socials import SocialService
from services.users import UserService


router = APIRouter(
    prefix='/api/v1/users',
    tags=['users'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
    responses={404: {'description': 'Not found'}, 401: {'description': 'Unauthorized'}},
)


@router.get('/', response_model=Page[UserRead])
@cache()
async def get_all(user_filter: UserFilter = FilterDepends(UserFilter), service: UserService = Depends()) -> Page[UserRead]:
    return await service.find_all(user_filter)


@router.get('/me', response_model=UserRead)
@cache()
async def get_me(user: UserRead = Depends(get_current_user)) -> UserRead:
    return user


@router.put('/me', response_model=UserRead)
async def update_me(
    user_data: UserUpdate, current_user: UserRead = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    user = await verify_credentials(current_user.uuid, user_data, service)
    user = await service.update(user, user_data)
    return UserRead.model_validate(user)


@router.patch('/me', response_model=UserRead)
async def patch_me(
    user_data: UserUpdatePartial, current_user: UserRead = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    user = await verify_credentials(current_user.uuid, user_data, service)
    user = await service.update(user, user_data, partial=True)
    return UserRead.model_validate(user)


@router.get('/{uuid}', response_model=UserRead)
@cache()
async def get_one(uuid: UUID4 | str, service: UserService = Depends()) -> UserRead:
    user = await service.find_by_uuid(uuid, detail='User does not exist')
    return UserRead.model_validate(user)


@router.put(
    '/{uuid}',
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def update_one(uuid: UUID4 | str, user_data: UserAdminUpdate, service: UserService = Depends()) -> UserRead:
    user = await verify_credentials(uuid, user_data, service)
    user = await service.update(user, user_data)
    return UserRead.model_validate(user)


@router.patch(
    '/{uuid}',
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_one(uuid: UUID4 | str, user_data: UserAdminUpdatePartial, service: UserService = Depends()) -> UserRead:
    user = await verify_credentials(uuid, user_data, service)
    user = await service.update(user, user_data, partial=True)
    return UserRead.model_validate(user)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4 | str, service: UserService = Depends()) -> None:
    user = await service.find_by_uuid(uuid, detail='User does not exist')
    if user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Attempt to delete admin user')
    await service.delete(user)


@router.get(
    '/{uuid}/socials',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_user_socials(uuid: UUID4, service: SocialService = Depends()) -> SocialRead:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    return SocialRead.model_validate(social)


@router.put(
    '/{uuid}/socials',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def update_user_socials(
    uuid: UUID4 | str, social_data: SocialAdminUpdate, service: SocialService = Depends()
) -> SocialRead:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    social = await service.update(social, social_data)
    return SocialRead.model_validate(social)


@router.patch(
    '/{uuid}/socials',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_user_socials(
    uuid: UUID4 | str, social_data: SocialAdminUpdatePartial, service: SocialService = Depends()
) -> SocialRead:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    social = await service.update(social, social_data, partial=True)
    return SocialRead.model_validate(social)
