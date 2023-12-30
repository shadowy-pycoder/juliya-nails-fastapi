from typing import Any, Type, TypeVar, Generic

from fastapi import Depends
from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.links import Page
from pydantic import UUID4, BaseModel
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models.base import BaseDBModel
from schemas.users import UserRead

BaseModelType = TypeVar('BaseModelType', bound=BaseDBModel)
BaseSchemaType = TypeVar('BaseSchemaType', bound=BaseModel)
BaseSchemaCreateType = TypeVar('BaseSchemaCreateType', bound=BaseModel)
BaseSchemaUpdateType = TypeVar('BaseSchemaUpdateType', bound=BaseModel)
BaseSchemaUpdatePartialType = TypeVar('BaseSchemaUpdatePartialType', bound=BaseModel)
BaseSchemaAdminUpdateType = TypeVar('BaseSchemaAdminUpdateType', bound=BaseModel)
BaseSchemaAdminUpdatePartialType = TypeVar('BaseSchemaAdminUpdatePartialType', bound=BaseModel)
BaseFilterType = TypeVar('BaseFilterType', bound=Filter)


class BaseService(
    Generic[
        BaseModelType,
        BaseSchemaType,
        BaseSchemaCreateType,
        BaseSchemaUpdateType,
        BaseSchemaUpdatePartialType,
        BaseSchemaAdminUpdateType,
        BaseSchemaAdminUpdatePartialType,
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
            transformer=lambda items: [UserRead.model_validate(item) for item in items],
        )

    async def find_by_uuid(self, uuid: UUID4 | str) -> BaseModelType | None:
        return await self.session.scalar(sa.select(self.model).filter_by(uuid=uuid))

    async def find_one_or_none(self, /, **filter_by: Any) -> BaseModelType | None:
        return await self.session.scalar(sa.select(self.model).filter_by(**filter_by))

    async def create(self, values: BaseSchemaCreateType) -> BaseModelType:
        new_instance = self.model(**values.model_dump())
        self.session.add(new_instance)
        await self.session.commit()
        await self.session.refresh(new_instance)
        return new_instance

    async def update(
        self,
        instance: BaseModelType,
        values: (
            BaseSchemaUpdateType | BaseSchemaUpdatePartialType | BaseSchemaAdminUpdateType | BaseSchemaAdminUpdatePartialType
        ),
        partial: bool = False,
    ) -> BaseModelType:
        instance.update(values.model_dump(exclude_unset=partial))
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: BaseModelType) -> None:
        await self.session.delete(instance)
        await self.session.commit()
