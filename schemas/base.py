from datetime import datetime

from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import UUID4


class BaseFilter(Filter):
    uuid: UUID4 | str | None = None
    created: datetime | None = None
    created__gt: datetime | None = None
    created__gte: datetime | None = None
    created__lt: datetime | None = None
    created__lte: datetime | None = None
    updated: datetime | None = None
    updated__gt: datetime | None = None
    updated__gte: datetime | None = None
    updated__lt: datetime | None = None
    updated__lte: datetime | None = None
    order_by: list[str] = ['created']
    search: str | None = None

    class Constants(Filter.Constants):
        pass
