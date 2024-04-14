from typing import TypeAlias

from src.models.services import Service
from src.repositories.base import BaseRepository
from src.schemas.services import (
    ServiceAdminUpdate,
    ServiceAdminUpdatePartial,
    ServiceCreate,
    ServiceFilter,
    ServiceRead,
    ServiceUpdate,
    ServiceUpdatePartial,
)


ServiceSchema: TypeAlias = ServiceUpdate | ServiceUpdatePartial | ServiceAdminUpdate | ServiceAdminUpdatePartial


class ServiceRepository(
    BaseRepository[
        Service,
        ServiceRead,
        ServiceCreate,
        ServiceUpdate,
        ServiceUpdatePartial,
        ServiceAdminUpdate,
        ServiceAdminUpdatePartial,
        ServiceFilter,
    ]
):
    model = Service
    schema = ServiceRead
    filter_type = ServiceFilter

    async def create(self, values: ServiceCreate) -> Service:
        await self.verify_uniqueness(values, ['name'])
        return await super().create(values)

    async def update(
        self,
        service: Service,
        values: ServiceSchema,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        exclude_defaults: bool = False,
    ) -> Service:
        await self.verify_uniqueness(values, ['name'], service)
        return await super().update(
            service,
            values,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )
