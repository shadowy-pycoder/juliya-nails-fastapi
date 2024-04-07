from typing import Any, TypeAlias

import sqlalchemy as sa
from fastapi import HTTPException, status
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.links import Page

from src.models.entries import Entry
from src.models.services import Service
from src.repositories.base import BaseRepository
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
from src.utils import get_url


EntrySchema: TypeAlias = EntryUpdate | EntryUpdatePartial | EntryAdminUpdate | EntryAdminUpdatePartial


class EntryRepository(
    BaseRepository[
        Entry,
        EntryRead,
        EntryCreate,
        EntryUpdate,
        EntryUpdatePartial,
        EntryAdminUpdate,
        EntryAdminUpdatePartial,
        EntryFilter,
    ]
):
    model = Entry
    schema = EntryRead
    filter_type = EntryFilter

    async def can_create_entry(self, instance: Entry, context: str = 'create') -> bool:
        filters = [Entry.date == instance.date, Entry.time <= instance.time]
        if context == 'update':
            filters.append(Entry.uuid != instance.uuid)
        prev_entry = await self.session.scalar(
            sa.select(Entry).filter(sa.and_(*filters)).order_by(Entry.date.desc(), Entry.time.desc())
        )
        if prev_entry and prev_entry.ending_time > instance.timestamp:
            return False
        next_entry = await self.session.scalar(
            sa.select(Entry)
            .filter(sa.and_(Entry.date == instance.date, Entry.time > instance.time))
            .order_by(Entry.date, Entry.time)
        )
        if next_entry and next_entry.timestamp < instance.ending_time:
            return False
        return True

    async def create(self, values: EntryCreate, **kwargs: Any) -> Entry:
        new_instance = self.model(**values.model_dump(exclude={'services'}), **kwargs)
        services = await self.session.scalars(sa.select(Service).filter(Service.uuid.in_(values.services)))
        new_instance.services.extend(services)
        if not await self.can_create_entry(new_instance):
            url = get_url('entries', 'get_by_date', date=values.date.strftime('%Y-%m-%d'))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f'Please choose different date or time. See all entries for this date: {url}',
            )
        self.session.add(new_instance)
        await self.session.commit()
        await self.session.refresh(new_instance)
        return new_instance

    async def update(
        self,
        entry: Entry,
        values: EntrySchema,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        exclude_defaults: bool = False,
    ) -> Entry:
        entry.update(
            values.model_dump(
                exclude={'services'},
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
                exclude_defaults=exclude_defaults,
            )
        )
        if values.services is not None:
            services = await self.session.scalars(sa.select(Service).filter(Service.uuid.in_(values.services)))
            entry.services.clear()
            entry.services.extend(services)
        if not await self.can_create_entry(entry, context='update'):
            url = get_url('entries', 'get_by_date', date=entry.date.strftime('%Y-%m-%d'))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f'Please choose different date or time. See all entries for this date: {url}',
            )
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def find_all_public(self, **filter_by: Any) -> Page[EntryInfo]:
        return await paginate(
            self.session,
            sa.select(self.model).filter_by(**filter_by),
            transformer=lambda items: [EntryInfo.model_validate(item) for item in items],
        )
