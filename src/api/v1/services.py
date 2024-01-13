from fastapi import APIRouter, Response, status, Depends
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi.logger import logger
from fastapi_pagination.links import Page
from pydantic import UUID4

from src.api.v1.dependencies import get_current_user, get_admin_user, get_active_user
from src.repositories.entries import EntryRepository
from src.repositories.services import ServiceRepository
from src.schemas.entries import EntryRead
from src.schemas.services import (
    ServiceRead,
    ServiceCreate,
    ServiceFilter,
    ServiceAdminUpdate,
    ServiceAdminUpdatePartial,
)


router = APIRouter(
    prefix='/v1/services',
    tags=['services'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
)


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def create_one(
    response: Response,
    service_data: ServiceCreate,
    repo: ServiceRepository = Depends(),
) -> ServiceRead:
    service = await repo.create(service_data)
    response.headers['Location'] = router.url_path_for('get_one', uuid=service.uuid)
    logger.info(f'[new service]: {service}')
    return ServiceRead.model_validate(service)


@router.get('/', status_code=status.HTTP_200_OK, response_model=Page[ServiceRead])
@cache()
async def get_all(
    service_filter: ServiceFilter = FilterDepends(ServiceFilter),
    repo: ServiceRepository = Depends(),
) -> Page[ServiceRead]:
    return await repo.find_all(service_filter)


@router.get('/{uuid}', status_code=status.HTTP_200_OK, response_model=ServiceRead)
@cache()
async def get_one(uuid: UUID4, repo: ServiceRepository = Depends()) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    return ServiceRead.model_validate(service)


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
async def get_service_entries(
    uuid: UUID4,
    service_repo: ServiceRepository = Depends(),
    entry_repo: EntryRepository = Depends(),
) -> Page[EntryRead]:
    service = await service_repo.find_by_uuid(uuid)
    return await entry_repo.find_many(service.entries)


@router.put(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one(
    uuid: UUID4 | str,
    service_data: ServiceAdminUpdate,
    repo: ServiceRepository = Depends(),
) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    service = await repo.update(service, service_data)
    logger.info(f'[update service]: {service}')
    return ServiceRead.model_validate(service)


@router.patch(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=ServiceRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one(
    uuid: UUID4 | str,
    service_data: ServiceAdminUpdatePartial,
    repo: ServiceRepository = Depends(),
) -> ServiceRead:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    service = await repo.update(service, service_data, exclude_unset=True)
    logger.info(f'[patch service]: {service}')
    return ServiceRead.model_validate(service)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def delete_one(uuid: UUID4 | str, repo: ServiceRepository = Depends()) -> None:
    service = await repo.find_by_uuid(uuid, detail='Service does not exist')
    logger.info(f'[delete service]: {service}')
    await repo.delete(service)
