from __future__ import annotations
from datetime import datetime
from functools import cached_property
from typing import Annotated
import uuid  # noqa: F401

from pydantic import BaseModel, UUID4, Field, computed_field, AfterValidator, ConfigDict


from models.posts import Post
from schemas.base import BaseFilter
from schemas.users import UserInfoSchema


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
        from api.v1.posts import router

        return router.url_path_for('get_one', uuid=self.uuid)


class PostCreate(BasePost):
    author_id: UUID4 | Annotated[str, AfterValidator(lambda x: uuid.UUID(x, version=4))]


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
