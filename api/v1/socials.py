from fastapi import APIRouter, status, Depends
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user
from schemas.socials import SocialRead, SocialFilter, SocialAdminUpdate, SocialAdminUpdatePartial
from services.socials import SocialService


router = APIRouter(
    prefix='/api/v1/socials',
    tags=['socials'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
    responses={404: {'description': 'Not found'}, 401: {'description': 'Unauthorized'}},
)


@router.get(
    '/',
    response_model=Page[SocialRead],
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_all(
    social_filter: SocialFilter = FilterDepends(SocialFilter), service: SocialService = Depends()
) -> Page[SocialRead]:
    return await service.find_all(social_filter)


@router.get(
    '/{uuid}',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
@cache()
async def get_one(uuid: UUID4, service: SocialService = Depends()) -> SocialRead:
    social = await service.find_by_uuid(uuid, detail='Social page does not exist')
    return SocialRead.model_validate(social)


@router.put(
    '/{uuid}',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def update_one(uuid: UUID4 | str, social_data: SocialAdminUpdate, service: SocialService = Depends()) -> SocialRead:
    social = await service.find_by_uuid(uuid, detail='Social page does not exist')
    social = await service.update(social, social_data)
    return SocialRead.model_validate(social)


@router.patch(
    '/{uuid}',
    response_model=SocialRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_one(uuid: UUID4 | str, social_data: SocialAdminUpdatePartial, service: SocialService = Depends()) -> SocialRead:
    social = await service.find_by_uuid(uuid, detail='Social page does not exist')
    social = await service.update(social, social_data, exclude_unset=True)
    return SocialRead.model_validate(social)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4 | str, service: SocialService = Depends()) -> None:
    social = await service.find_by_uuid(uuid, detail='Social page does not exist')
    await service.delete(social)
