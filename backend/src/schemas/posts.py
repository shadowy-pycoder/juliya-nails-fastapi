from __future__ import annotations

import uuid  # noqa: F401
from datetime import datetime
from functools import cached_property
from typing import Annotated

from pydantic import UUID4, AfterValidator, BaseModel, ConfigDict, Field, computed_field

from src.models.posts import Post
from src.schemas.base import BaseFilter, UUIDstr
from src.schemas.users import UserInfoSchema
from src.utils import get_url


class BasePost(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: Annotated[str, Field(min_length=2, max_length=100)]
    image: Annotated[str, Field(max_length=50)]
    content: Annotated[str, Field(min_length=2)]


class PostRead(BasePost):
    uuid: UUID4 | str
    author: UserInfoSchema
    created: datetime
    updated: datetime

    @computed_field  # type: ignore[misc]
    @cached_property
    def url(self) -> str:
        return get_url('posts', uuid=self.uuid)


class PostCreate(BasePost):
    author_id: UUIDstr


class PostUpdatePartial(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: Annotated[str | None, Field(min_length=2, max_length=100)] = None
    image: Annotated[str | None, Field(max_length=50)] = None
    content: Annotated[str | None, Field(min_length=2)] = None


class PostUpdate(BasePost):
    pass


class PostAdminUpdatePartial(PostUpdatePartial):
    pass


class PostAdminUpdate(PostUpdate):
    pass


class PostFilter(BaseFilter):
    author_id: Annotated[UUID4, AfterValidator(lambda x: str(x))] | str | None = None
    title: str | None = None
    title__ilike: str | None = None
    title__like: str | None = None
    title__neq: str | None = None
    title__in: list[str] | None = None
    title__nin: list[str] | None = None
    content__ilike: str | None = None
    content__like: str | None = None

    class Constants(BaseFilter.Constants):
        model = Post
        search_model_fields = ['title']
