from typing import Any, Type, TypeVar, Generic

from fastapi import Depends, status, HTTPException
from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.links import Page
from pydantic import UUID4, BaseModel
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute, WriteOnlyCollection

from src.database import get_async_session
from src.models.base import BaseDBModel

BaseModelType = TypeVar('BaseModelType', bound=BaseDBModel)
BaseSchemaType = TypeVar('BaseSchemaType', bound=BaseModel)
BaseSchemaCreate = TypeVar('BaseSchemaCreate', bound=BaseModel)
BaseSchemaUpdate = TypeVar('BaseSchemaUpdate', bound=BaseModel)
BaseSchemaUpdatePartial = TypeVar('BaseSchemaUpdatePartial', bound=BaseModel)
BaseSchemaAdminUpdate = TypeVar('BaseSchemaAdminUpdate', bound=BaseModel)
BaseSchemaAdminUpdatePartial = TypeVar('BaseSchemaAdminUpdatePartial', bound=BaseModel)
BaseFilterType = TypeVar('BaseFilterType', bound=Filter)


class BaseRepository(
    Generic[
        BaseModelType,
        BaseSchemaType,
        BaseSchemaCreate,
        BaseSchemaUpdate,
        BaseSchemaUpdatePartial,
        BaseSchemaAdminUpdate,
        BaseSchemaAdminUpdatePartial,
        BaseFilterType,
    ]
):
    model: Type[BaseModelType]
    schema: Type[BaseSchemaType]
    filter_type: Type[BaseFilterType]

    def __init__(self, session: AsyncSession = Depends(get_async_session)) -> None:
        self.session = session

    async def find_all(self, model_filter: BaseFilterType) -> Page[BaseSchemaType]:
        query = sa.select(self.model)
        query = model_filter.filter(query)
        query = model_filter.sort(query)
        return await paginate(
            self.session,
            query,
            transformer=lambda items: [self.schema.model_validate(item) for item in items],
        )

    async def find_by_uuid(self, uuid: UUID4 | str, detail: str = 'Not found') -> BaseModelType:
        result = await self.session.scalar(sa.select(self.model).filter_by(uuid=uuid))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return result

    async def find_one(self, detail: str = 'Not found', **filter_by: Any) -> BaseModelType:
        result = await self.session.scalar(sa.select(self.model).filter_by(**filter_by))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return result

    async def find_many(
        self, collection: WriteOnlyCollection[Any] | None = None, **filter_by: Any
    ) -> Page[BaseSchemaType]:
        query = sa.select(self.model) if collection is None else collection.select()
        return await paginate(
            self.session,
            query.filter_by(**filter_by),
            transformer=lambda items: [self.schema.model_validate(item) for item in items],
        )

    async def create(self, values: BaseSchemaCreate) -> BaseModelType:
        new_instance = self.model(**values.model_dump())
        self.session.add(new_instance)
        await self.session.commit()
        await self.session.refresh(new_instance)
        return new_instance

    async def update(
        self,
        instance: BaseModelType,
        values: BaseSchemaUpdate
        | BaseSchemaUpdatePartial
        | BaseSchemaAdminUpdate
        | BaseSchemaAdminUpdatePartial,
        exclude_unset: bool = False,
        exclude_none: bool = False,
    ) -> BaseModelType:
        instance.update(values.model_dump(exclude_unset=exclude_unset, exclude_none=exclude_none))
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: BaseModelType) -> None:
        await self.session.delete(instance)
        await self.session.commit()

    async def unique(self, field: str, value: Any) -> bool:
        attr: QueryableAttribute[Any] = getattr(self.model, field)
        result = await self.session.scalar(sa.select(self.model).filter(attr.ilike(value)))
        return result is None

    async def verify_uniqueness(
        self,
        values: BaseSchemaUpdate
        | BaseSchemaUpdatePartial
        | BaseSchemaAdminUpdate
        | BaseSchemaAdminUpdatePartial
        | BaseSchemaCreate,
        fields: list[str],
        instance: BaseModelType | None = None,
    ) -> None:
        errors = []
        for field_name in fields:
            field_value = getattr(values, field_name, None)
            if field_value and (field_value != getattr(instance, field_name) if instance else True):
                if not await self.unique(field_name, field_value):
                    errors.append(f'Please choose a different {field_name}')
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='\n'.join(e for e in errors),
            )
