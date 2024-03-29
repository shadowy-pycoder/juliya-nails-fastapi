from datetime import datetime
from functools import cached_property
from typing import Annotated

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from src.models.services import Service
from src.schemas.base import BaseFilter
from src.utils import get_url


class BaseServiceValidation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator('name', mode='after', check_fields=False)
    @classmethod
    def capitalize(cls, v: str) -> str | None:
        return v.capitalize() if v else None


class BaseService(BaseServiceValidation):
    name: Annotated[str, Field(min_length=2, max_length=64)]
    duration: Annotated[int, Field(gte=10)]


class ServiceRead(BaseService):
    uuid: UUID4 | str
    created: datetime
    updated: datetime

    @computed_field  # type: ignore[misc]
    @cached_property
    def url(self) -> str:
        return get_url('services', uuid=self.uuid)

    @computed_field  # type: ignore[misc]
    @cached_property
    def entries(self) -> str:
        return get_url('services', 'get_service_entries', uuid=self.uuid)


class ServiceCreate(BaseService):
    pass


class ServiceUpdatePartial(BaseServiceValidation):
    name: Annotated[str | None, Field(min_length=2, max_length=64)] = None
    duration: Annotated[int, Field(gte=10)] | None = None


class ServiceUpdate(BaseService):
    name: Annotated[str, Field(min_length=2, max_length=64)]
    duration: Annotated[int, Field(gte=10)]


class ServiceAdminUpdatePartial(ServiceUpdatePartial):
    pass


class ServiceAdminUpdate(ServiceUpdate):
    pass


class ServiceFilter(BaseFilter):
    name: str | None = None
    name__ilike: str | None = None
    name__like: str | None = None
    name__neq: str | None = None
    name__in: list[str] | None = None
    name__nin: list[str] | None = None
    duration: datetime | None = None
    duration__gt: datetime | None = None
    duration__gte: datetime | None = None
    duration__lt: datetime | None = None
    duration__lte: datetime | None = None

    class Constants(BaseFilter.Constants):
        model = Service
        search_model_fields = ['name', 'duration']
