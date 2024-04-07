from fastapi import APIRouter, Depends, status
from fastapi.logger import logger
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from pydantic import UUID4

from src.api.v1.dependencies import get_active_user, get_admin_user, get_current_user
from src.repositories.socials import SocialRepository
from src.schemas.socials import (
    SocialAdminUpdate,
    SocialAdminUpdatePartial,
    SocialFilter,
    SocialRead,
)


router = APIRouter(
    prefix='/v1/socials',
    tags=['socials'],
    dependencies=[
        Depends(get_current_user),
        Depends(get_active_user),
        Depends(get_admin_user),
    ],
)


@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_model=Page[SocialRead],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_all(
    social_filter: SocialFilter = FilterDepends(SocialFilter), repo: SocialRepository = Depends()
) -> Page[SocialRead]:
    return await repo.find_all(social_filter)


@router.get(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_one(uuid: UUID4, repo: SocialRepository = Depends()) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    return SocialRead.model_validate(social)


@router.put(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one(
    uuid: UUID4 | str, social_data: SocialAdminUpdate, repo: SocialRepository = Depends()
) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data)
    logger.info(f'[update social][admin]: {social}')
    return SocialRead.model_validate(social)


@router.patch(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=SocialRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one(
    uuid: UUID4 | str, social_data: SocialAdminUpdatePartial, repo: SocialRepository = Depends()
) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data, exclude_unset=True)
    logger.info(f'[patch social][admin]: {social}')
    return SocialRead.model_validate(social)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def delete_one(uuid: UUID4 | str, repo: SocialRepository = Depends()) -> None:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    logger.info(f'[delete social][admin]: {social}')
    await repo.delete(social)
