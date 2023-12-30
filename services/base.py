from typing import Any, Type, TypeVar, Generic

from fastapi import Depends
from pydantic import UUID4, BaseModel
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session
from models.base import BaseDBModel

BaseModelType = TypeVar('BaseModelType', bound=BaseDBModel)
BaseSchemaType = TypeVar('BaseSchemaType', bound=BaseModel)
BaseSchemaCreateType = TypeVar('BaseSchemaCreateType', bound=BaseModel)
BaseSchemaUpdateType = TypeVar('BaseSchemaUpdateType', bound=BaseModel)
BaseSchemaUpdatePartialType = TypeVar('BaseSchemaUpdatePartialType', bound=BaseModel)
BaseSchemaAdminUpdateType = TypeVar('BaseSchemaAdminUpdateType', bound=BaseModel)
BaseSchemaAdminUpdatePartialType = TypeVar('BaseSchemaAdminUpdatePartialType', bound=BaseModel)


class BaseService(
    Generic[
        BaseModelType,
        BaseSchemaType,
        BaseSchemaCreateType,
        BaseSchemaUpdateType,
        BaseSchemaUpdatePartialType,
        BaseSchemaAdminUpdateType,
        BaseSchemaAdminUpdatePartialType,
    ]
):
    model: Type[BaseModelType]

    def __init__(self, session: AsyncSession = Depends(get_async_session)) -> None:
        self.session = session

    async def find_all(self, /, **filter_by: Any) -> list[BaseModelType]:
        result = await self.session.scalars(sa.select(self.model).filter_by(**filter_by))
        return list(result.all())

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
