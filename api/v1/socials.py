from fastapi import APIRouter, status, Depends
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user
from repositories.socials import SocialRepository
from schemas.socials import SocialRead, SocialFilter, SocialAdminUpdate, SocialAdminUpdatePartial


router = APIRouter(
    prefix='/api/v1/socials',
    tags=['socials'],
    dependencies=[
        Depends(get_current_user),
        Depends(get_active_user),
        Depends(get_admin_user),
    ],
)


@router.get(
    '/',
    response_model=Page[SocialRead],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_all(
    social_filter: SocialFilter = FilterDepends(SocialFilter), repo: SocialRepository = Depends()
) -> Page[SocialRead]:
    return await repo.find_all(social_filter)


@router.get(
    '/{uuid}',
    response_model=SocialRead,
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_one(uuid: UUID4, repo: SocialRepository = Depends()) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    return SocialRead.model_validate(social)


@router.put(
    '/{uuid}',
    response_model=SocialRead,
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def update_one(uuid: UUID4 | str, social_data: SocialAdminUpdate, repo: SocialRepository = Depends()) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data)
    return SocialRead.model_validate(social)


@router.patch(
    '/{uuid}',
    response_model=SocialRead,
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_one(uuid: UUID4 | str, social_data: SocialAdminUpdatePartial, repo: SocialRepository = Depends()) -> SocialRead:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    social = await repo.update(social, social_data, exclude_unset=True)
    return SocialRead.model_validate(social)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4 | str, repo: SocialRepository = Depends()) -> None:
    social = await repo.find_by_uuid(uuid, detail='Social page does not exist')
    await repo.delete(social)
