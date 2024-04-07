from datetime import date as date_

from fastapi import APIRouter, Depends, Response, status
from fastapi.logger import logger
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page

from src.api.v1.dependencies import (
    get_active_user,
    get_admin_user,
    get_confirmed_user,
    get_current_user,
    validate_entry,
)
from src.models.entries import Entry
from src.models.users import User
from src.repositories.entries import EntryRepository
from src.schemas.entries import (
    EntryAdminUpdate,
    EntryAdminUpdatePartial,
    EntryCreate,
    EntryFilter,
    EntryInfo,
    EntryRead,
    EntryUpdate,
    EntryUpdatePartial,
)


router = APIRouter(
    prefix='/v1/entries',
    tags=['entries'],
    dependencies=[
        Depends(get_current_user),
        Depends(get_active_user),
        Depends(get_confirmed_user),
    ],
)


@router.post('/', status_code=status.HTTP_201_CREATED, response_model=EntryRead)
async def create_one(
    response: Response,
    entry_data: EntryCreate,
    repo: EntryRepository = Depends(),
    user: User = Depends(get_current_user),
) -> EntryRead:
    entry = await repo.create(entry_data, user_id=user.uuid)
    response.headers['Location'] = router.url_path_for('get_one', uuid=entry.uuid)
    logger.info(f'[new entry]: {entry}')
    return EntryRead.model_validate(entry)


@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_model=Page[EntryRead],
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_all(
    entry_filter: EntryFilter = FilterDepends(EntryFilter),
    repo: EntryRepository = Depends(),
) -> Page[EntryRead]:
    return await repo.find_all(entry_filter)


@router.get(
    '/date/{date}',
    status_code=status.HTTP_200_OK,
    response_model=Page[EntryInfo],
)
@cache()
async def get_by_date(date: date_, repo: EntryRepository = Depends()) -> Page[EntryInfo]:
    return await repo.find_all_public(date=date)


@router.get(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=EntryRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
@cache()
async def get_one(entry: Entry = Depends(validate_entry)) -> EntryRead:
    return EntryRead.model_validate(entry)


@router.put(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=EntryRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one(
    entry_data: EntryUpdate,
    entry: Entry = Depends(validate_entry),
    repo: EntryRepository = Depends(),
) -> EntryRead:
    entry = await repo.update(entry, entry_data)
    logger.info(f'[update entry]: {entry}')
    return EntryRead.model_validate(entry)


@router.patch(
    '/{uuid}',
    status_code=status.HTTP_200_OK,
    response_model=EntryRead,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one(
    entry_data: EntryUpdatePartial,
    entry: Entry = Depends(validate_entry),
    repo: EntryRepository = Depends(),
) -> EntryRead:
    entry = await repo.update(entry, entry_data, exclude_unset=True)
    logger.info(f'[patch entry]: {entry}')
    return EntryRead.model_validate(entry)


@router.put(
    '/{uuid}/edit',
    status_code=status.HTTP_200_OK,
    response_model=EntryRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one_admin(
    entry_data: EntryAdminUpdate,
    entry: Entry = Depends(validate_entry),
    repo: EntryRepository = Depends(),
) -> EntryRead:
    entry = await repo.update(entry, entry_data)
    logger.info(f'[update entry][admin]: {entry}')
    return EntryRead.model_validate(entry)


@router.patch(
    '/{uuid}/edit',
    status_code=status.HTTP_200_OK,
    response_model=EntryRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one_admin(
    entry_data: EntryAdminUpdatePartial,
    entry: Entry = Depends(validate_entry),
    repo: EntryRepository = Depends(),
) -> EntryRead:
    entry = await repo.update(entry, entry_data, exclude_unset=True)
    logger.info(f'[patch entry][admin]: {entry}')
    return EntryRead.model_validate(entry)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {'description': 'You are not allowed to perform this operation'},
    },
)
async def delete_one(
    entry: Entry = Depends(validate_entry),
    repo: EntryRepository = Depends(),
) -> None:
    logger.info(f'[delete entry]: {entry}')
    await repo.delete(entry)
