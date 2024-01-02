from fastapi import APIRouter, status, Depends, HTTPException, UploadFile
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from fastapi.responses import FileResponse
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user, verify_credentials
from models.users import User
from schemas.posts import PostRead
from schemas.socials import SocialRead, SocialAdminUpdate, SocialAdminUpdatePartial, SocialUpdate, SocialUpdatePartial
from schemas.users import UserRead, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter
from services.posts import PostService
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
    user_data: UserUpdate, current_user: User = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    await verify_credentials(current_user, user_data, service)
    user = await service.update(current_user, user_data)
    return UserRead.model_validate(user)


@router.patch('/me', response_model=UserRead)
async def patch_me(
    user_data: UserUpdatePartial, current_user: User = Depends(get_current_user), service: UserService = Depends()
) -> UserRead:
    await verify_credentials(current_user, user_data, service)
    user = await service.update(current_user, user_data, exclude_unset=True)
    return UserRead.model_validate(user)


@router.get('/me/posts', response_model=list[PostRead])
@cache()
async def get_my_posts(user: User = Depends(get_current_user), service: PostService = Depends()) -> list[PostRead]:
    return await service.find_many(author_id=user.uuid)


@router.get('/me/socials', response_model=SocialRead)
@cache()
async def get_my_socials(user: User = Depends(get_current_user)) -> SocialRead:
    return SocialRead.model_validate(user.socials)


@router.put(
    '/me/socials',
    response_model=SocialRead,
)
async def update_my_socials(
    social_data: SocialUpdate, user: User = Depends(get_current_user), service: SocialService = Depends()
) -> SocialRead:
    social = await service.update(user.socials, social_data)
    return SocialRead.model_validate(social)


@router.patch(
    '/me/socials',
    response_model=SocialRead,
)
async def patch_my_socials(
    social_data: SocialUpdatePartial, user: User = Depends(get_current_user), service: SocialService = Depends()
) -> SocialRead:
    social = await service.update(user.socials, social_data, exclude_unset=True)
    return SocialRead.model_validate(social)


@router.get(
    '/me/socials/avatar',
    response_class=FileResponse,
)
async def get_my_avatar(user: User = Depends(get_current_user), service: SocialService = Depends()) -> FileResponse:
    return FileResponse(service.get_avatar(user.socials))


@router.put(
    '/me/socials/avatar',
    response_model=SocialRead,
    responses={413: {'description': 'Too large'}, 415: {'description': 'Unsupported file type'}},
)
async def update_my_avatar(
    file: UploadFile, user: User = Depends(get_current_user), service: SocialService = Depends()
) -> SocialRead:
    await service.update_avatar(user.socials, file)
    return SocialRead.model_validate(user.socials)


@router.delete('/me/socials/avatar', status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_avatar(user: User = Depends(get_current_user), service: SocialService = Depends()) -> None:
    await service.delete_avatar(user.socials)


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
    user = await service.find_by_uuid(uuid, detail='User does not exist')
    await verify_credentials(user, user_data, service)
    user = await service.update(user, user_data)
    return UserRead.model_validate(user)


@router.patch(
    '/{uuid}',
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_one(uuid: UUID4 | str, user_data: UserAdminUpdatePartial, service: UserService = Depends()) -> UserRead:
    user = await service.find_by_uuid(uuid, detail='User does not exist')
    await verify_credentials(user, user_data, service)
    user = await service.update(user, user_data, exclude_unset=True)
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
    '/{uuid}/posts',
    response_model=list[PostRead],
)
@cache()
async def get_user_posts(uuid: UUID4 | str, service: PostService = Depends()) -> list[PostRead]:
    return await service.find_many(author_id=uuid)


@router.get(
    '/{uuid}/socials',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_user_socials(uuid: UUID4 | str, service: SocialService = Depends()) -> SocialRead:
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
    social = await service.update(social, social_data, exclude_unset=True)
    return SocialRead.model_validate(social)


@router.get(
    '/{uuid}/socials/avatar',
    response_class=FileResponse,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def get_user_avatar(uuid: UUID4 | str, service: SocialService = Depends()) -> FileResponse:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    return FileResponse(service.get_avatar(social))


@router.put(
    '/{uuid}/socials/avatar',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        413: {'description': 'Too large'},
        415: {'description': 'Unsupported file type'},
        403: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_user_avatar(uuid: UUID4 | str, file: UploadFile, service: SocialService = Depends()) -> SocialRead:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    await service.update_avatar(social, file)
    return SocialRead.model_validate(social)


@router.delete(
    '/{uuid}/socials/avatar',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_user_avatar(uuid: UUID4 | str, service: SocialService = Depends()) -> None:
    social = await service.find_one(user_id=uuid, detail='Social page does not exist')
    await service.delete_avatar(social)
