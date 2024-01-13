from fastapi import APIRouter, status, Depends, HTTPException, UploadFile
from fastapi.background import BackgroundTasks
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi.logger import logger
from fastapi_pagination.links import Page
from fastapi.responses import FileResponse
from pydantic import UUID4

from src.api.v1.dependencies import (
    get_current_user,
    get_admin_user,
    get_active_user,
    get_confirmed_user,
    check_disposable,
)
from src.models.users import User
from src.repositories.auth import AuthRepository
from src.repositories.entries import EntryRepository
from src.repositories.posts import PostRepository
from src.repositories.socials import SocialRepository
from src.repositories.users import UserRepository
from src.schemas.posts import PostRead
from src.schemas.entries import EntryRead
from src.schemas.socials import (
    SocialRead,
    SocialAdminUpdate,
    SocialAdminUpdatePartial,
    SocialUpdate,
    SocialUpdatePartial,
)
from src.schemas.users import (
    UserRead,
    UserUpdate,
    UserUpdatePartial,
    UserAdminUpdate,
    UserAdminUpdatePartial,
    UserFilter,
)


router = APIRouter(
    prefix='/v1/users',
    tags=['users'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
)


@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_model=Page[UserRead],
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_all(
    user_filter: UserFilter = FilterDepends(UserFilter),
    repo: UserRepository = Depends(),
) -> Page[UserRead]:
    return await repo.find_all(user_filter)


@router.get('/me', status_code=status.HTTP_200_OK, response_model=UserRead)
@cache()
async def get_me(user: UserRead = Depends(get_current_user)) -> UserRead:
    return user


@router.put(
    '/me',
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    dependencies=[Depends(check_disposable)],
    responses={
        status.HTTP_400_BAD_REQUEST: {'description': 'Disposable domains are not allowed'},
    },
)
async def update_me(
    user_data: UserUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(),
    auth_repo: AuthRepository = Depends(),
) -> UserRead:
    user = await user_repo.update_with_confirmation(
        current_user,
        user_data,
        auth_repo,
        background_tasks,
    )
    logger.info(f'[update me]: {user}')
    return UserRead.model_validate(user)


@router.patch(
    '/me',
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    dependencies=[Depends(check_disposable)],
    responses={
        status.HTTP_400_BAD_REQUEST: {'description': 'Disposable domains are not allowed'},
    },
)
async def patch_me(
    user_data: UserUpdatePartial,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(),
    auth_repo: AuthRepository = Depends(),
) -> UserRead:
    user = await user_repo.update_with_confirmation(
        current_user,
        user_data,
        auth_repo,
        background_tasks,
        exclude_unset=True,
    )
    logger.info(f'[patch me]: {user}')
    return UserRead.model_validate(user)


@router.get(
    '/me/entries',
    status_code=status.HTTP_200_OK,
    response_model=Page[EntryRead],
    dependencies=[Depends(get_confirmed_user)],
)
@cache()
async def get_my_entries(
    user: User = Depends(get_current_user),
    repo: EntryRepository = Depends(),
) -> Page[EntryRead]:
    return await repo.find_many(user.entries)


@router.get('/me/posts', status_code=status.HTTP_200_OK, response_model=Page[PostRead])
@cache()
async def get_my_posts(
    user: User = Depends(get_current_user),
    repo: PostRepository = Depends(),
) -> Page[PostRead]:
    return await repo.find_many(user.posts)


@router.get('/me/socials', status_code=status.HTTP_200_OK, response_model=SocialRead)
@cache()
async def get_my_socials(user: User = Depends(get_current_user)) -> SocialRead:
    return SocialRead.model_validate(user.socials)


@router.put(
    '/me/socials',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_confirmed_user)],
)
async def update_my_socials(
    social_data: SocialUpdate,
    user: User = Depends(get_current_user),
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.update(user.socials, social_data)
    logger.info(f'[update my socials]: {social}')
    return SocialRead.model_validate(social)


@router.patch(
    '/me/socials',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_confirmed_user)],
)
async def patch_my_socials(
    social_data: SocialUpdatePartial,
    user: User = Depends(get_current_user),
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.update(user.socials, social_data, exclude_unset=True)
    logger.info(f'[patch my socials]: {social}')
    return SocialRead.model_validate(social)


@router.get(
    '/me/socials/avatar',
    status_code=status.HTTP_200_OK,
    response_class=FileResponse,
)
async def get_my_avatar(
    user: User = Depends(get_current_user),
    repo: SocialRepository = Depends(),
) -> FileResponse:
    return FileResponse(repo.get_avatar(user.socials))


@router.put(
    '/me/socials/avatar',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_confirmed_user)],
    responses={
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {'description': 'Too large'},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {'description': 'Unsupported file type'},
    },
)
async def update_my_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    repo: SocialRepository = Depends(),
) -> SocialRead:
    await repo.update_avatar(user.socials, file)
    return SocialRead.model_validate(user.socials)


@router.delete(
    '/me/socials/avatar',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_confirmed_user)],
)
async def delete_my_avatar(
    user: User = Depends(get_current_user),
    repo: SocialRepository = Depends(),
) -> None:
    await repo.delete_avatar(user.socials)


@router.get(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_one(uuid: UUID4 | str, repo: UserRepository = Depends()) -> UserRead:
    user = await repo.find_by_uuid(uuid, detail='User does not exist')
    return UserRead.model_validate(user)


@router.put(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one(
    uuid: UUID4 | str,
    user_data: UserAdminUpdate,
    repo: UserRepository = Depends(),
) -> UserRead:
    user = await repo.find_by_uuid(uuid, detail='User does not exist')
    user = await repo.update(user, user_data)
    logger.info(f'[update user][admin]: {user}')
    return UserRead.model_validate(user)


@router.patch(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=UserRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one(
    uuid: UUID4 | str,
    user_data: UserAdminUpdatePartial,
    repo: UserRepository = Depends(),
) -> UserRead:
    user = await repo.find_by_uuid(uuid, detail='User does not exist')
    user = await repo.update(user, user_data, exclude_unset=True)
    logger.info(f'[patch user][admin]: {user}')
    return UserRead.model_validate(user)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def delete_one(
    uuid: UUID4 | str,
    repo: UserRepository = Depends(),
) -> None:
    user = await repo.find_by_uuid(uuid, detail='User does not exist')
    if user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='Attempt to delete admin user'
        )
    logger.info(f'[delete user][admin]: {user}')
    await repo.delete(user)


@router.get(
    '/{uuid}/entries',
    status_code=status.HTTP_200_OK,
    response_model=Page[EntryRead],
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_user_entries(
    uuid: UUID4 | str,
    entry_repo: EntryRepository = Depends(),
    user_repo: UserRepository = Depends(),
) -> Page[EntryRead]:
    user = await user_repo.find_by_uuid(uuid)
    return await entry_repo.find_many(user.entries)


@router.get(
    '/{uuid}/posts',
    status_code=status.HTTP_200_OK,
    response_model=Page[PostRead],
    dependencies=[Depends(get_confirmed_user)],
)
@cache()
async def get_user_posts(
    uuid: UUID4 | str,
    post_repo: PostRepository = Depends(),
    user_repo: UserRepository = Depends(),
) -> Page[PostRead]:
    user = await user_repo.find_by_uuid(uuid)
    return await post_repo.find_many(user.posts)


@router.get(
    '/{uuid}/socials',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_user_socials(
    uuid: UUID4 | str,
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    return SocialRead.model_validate(social)


@router.put(
    '/{uuid}/socials',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_user_socials(
    uuid: UUID4 | str,
    social_data: SocialAdminUpdate,
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data)
    logger.info(f'[update user socials]: {social}')
    return SocialRead.model_validate(social)


@router.patch(
    '/{uuid}/socials',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_user_socials(
    uuid: UUID4 | str,
    social_data: SocialAdminUpdatePartial,
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data, exclude_unset=True)
    logger.info(f'[patch user socials]: {social}')
    return SocialRead.model_validate(social)


@router.get(
    '/{uuid}/socials/avatar',
    status_code=status.HTTP_200_OK,
    response_class=FileResponse,
    dependencies=[Depends(get_confirmed_user)],
)
async def get_user_avatar(
    uuid: UUID4 | str,
    repo: SocialRepository = Depends(),
) -> FileResponse:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    return FileResponse(repo.get_avatar(social))


@router.put(
    '/{uuid}/socials/avatar',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {'description': 'Too large'},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {'description': 'Unsupported file type'},
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_user_avatar(
    uuid: UUID4 | str,
    file: UploadFile,
    repo: SocialRepository = Depends(),
) -> SocialRead:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    await repo.update_avatar(social, file)
    return SocialRead.model_validate(social)


@router.delete(
    '/{uuid}/socials/avatar',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def delete_user_avatar(
    uuid: UUID4 | str,
    repo: SocialRepository = Depends(),
) -> None:
    social = await repo.find_one(user_id=uuid, detail='Social page does not exist')
    await repo.delete_avatar(social)
