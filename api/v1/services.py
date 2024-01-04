from fastapi import APIRouter, Response, status, Depends
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user
from repositories.entries import EntryRepository
from repositories.services import ServiceRepository
from schemas.entries import EntryRead
from schemas.services import ServiceRead, ServiceCreate, ServiceFilter, ServiceAdminUpdate, ServiceAdminUpdatePartial


router = APIRouter(
    prefix='/api/v1/services',
    tags=['services'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
    responses={404: {'description': 'Not found'}, 401: {'description': 'Unauthorized'}},
)


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        403: {'description': 'You are not allowed to perform this operation'},
    },
)
async def create_one(
    response: Response,
    service_data: ServiceCreate,
    repo: ServiceRepository = Depends(),
) -> ServiceRead:
    service = await repo.create(service_data)
    response.headers['Location'] = router.url_path_for('get_one', uuid=service.uuid)
    return ServiceRead.model_validate(service)


@router.get('/', response_model=Page[ServiceRead])
@cache()
async def get_all(
    service_filter: ServiceFilter = FilterDepends(ServiceFilter), repo: ServiceRepository = Depends()
) -> Page[ServiceRead]:
    return await repo.find_all(service_filter)


@router.get('/{uuid}', response_model=ServiceRead)
@cache()
async def get_one(uuid: UUID4, repo: ServiceRepository = Depends()) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    return ServiceRead.model_validate(service)


@router.get('/{uuid}/entries', response_model=Page[EntryRead])
@cache()
async def get_service_entries(
    uuid: UUID4, service_repo: ServiceRepository = Depends(), entry_repo: EntryRepository = Depends()
) -> Page[EntryRead]:
    service = await service_repo.find_by_uuid(uuid)
    return await entry_repo.find_many(service.entries)


@router.put(
    '/{uuid}',
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def update_one(uuid: UUID4 | str, service_data: ServiceAdminUpdate, repo: ServiceRepository = Depends()) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    service = await repo.update(service, service_data)
    return ServiceRead.model_validate(service)


@router.patch(
    '/{uuid}',
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def patch_one(
    uuid: UUID4 | str, service_data: ServiceAdminUpdatePartial, repo: ServiceRepository = Depends()
) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    service = await repo.update(service, service_data, exclude_unset=True)
    return ServiceRead.model_validate(service)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4 | str, repo: ServiceRepository = Depends()) -> None:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    await repo.delete(service)
