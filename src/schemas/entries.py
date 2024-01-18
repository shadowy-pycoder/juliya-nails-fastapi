from datetime import date as date_
from datetime import datetime
from datetime import time as time_
from functools import cached_property

from pydantic import UUID4, BaseModel, ConfigDict, computed_field, model_validator

from src.models.entries import Entry
from src.schemas.base import BaseFilter, UUIDstr
from src.schemas.services import ServiceRead
from src.schemas.users import UserInfoSchema
from src.utils import get_url


class BaseEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_
    time: time_

    @model_validator(mode='after')
    def validate_timestamp(self) -> 'BaseEntry':
        ts = datetime.combine(self.date, self.time).timestamp()
        if ts <= datetime.now().timestamp():
            raise ValueError('Date and time cannot be lower than current time')
        return self


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_
    time: time_
    uuid: UUID4 | str
    created: datetime
    updated: datetime
    user: UserInfoSchema
    services: list[ServiceRead]
    timestamp: float
    duration: int
    ending_time: float
    completed: bool

    @computed_field  # type: ignore[misc]
    @cached_property
    def url(self) -> str:
        return get_url('entries', uuid=self.uuid)


class EntryCreate(BaseEntry):
    services: list[UUIDstr]


class EntryUpdatePartial(BaseEntry):
    model_config = ConfigDict(from_attributes=True)

    services: list[UUIDstr] | None = None


class EntryUpdate(BaseEntry):
    services: list[UUIDstr]


class EntryAdminUpdatePartial(EntryUpdatePartial):
    completed: bool | None = None


class EntryAdminUpdate(EntryUpdate):
    completed: bool


class EntryInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_
    time: time_
    completed: bool


class EntryFilter(BaseFilter):
    date: date_ | None = None
    date__gt: date_ | None = None
    date__gte: date_ | None = None
    date__lt: date_ | None = None
    date__lte: date_ | None = None
    time: time_ | None = None
    time__gt: time_ | None = None
    time__gte: time_ | None = None
    time__lt: time_ | None = None
    time__lte: time_ | None = None
    timestamp: float | None = None
    timestamp__gt: float | None = None
    timestamp__gte: float | None = None
    timestamp__lt: float | None = None
    timestamp__lte: float | None = None
    duration: float | None = None
    duration__gt: float | None = None
    duration__gte: float | None = None
    duration__lt: float | None = None
    duration__lte: float | None = None
    ending_time: float | None = None
    ending_time__gt: float | None = None
    ending_time__gte: float | None = None
    ending_time__lt: float | None = None
    ending_time__lte: float | None = None
    completed: bool | None = None

    class Constants(BaseFilter.Constants):
        model = Entry
