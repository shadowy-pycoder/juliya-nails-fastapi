from __future__ import annotations
from datetime import datetime
from functools import cached_property
from typing import Annotated

from pydantic import (
    BaseModel,
    UUID4,
    Field,
    computed_field,
    ConfigDict,
    field_validator,
)

from src.models.socials import SocialMedia
from src.schemas.base import BaseFilter, UUIDstr
from src.schemas.users import UserInfoSchema
from src.utils import PATTERNS, get_url


class BaseSocial(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    first_name: Annotated[
        str | None, Field(min_length=2, max_length=50, pattern=PATTERNS['name'])
    ] = None
    last_name: Annotated[
        str | None, Field(min_length=2, max_length=50, pattern=PATTERNS['name'])
    ] = None
    phone_number: Annotated[
        str | None, Field(max_length=50, pattern=PATTERNS['phone_number'])
    ] = None
    viber: Annotated[str | None, Field(max_length=50, pattern=PATTERNS['phone_number'])] = None
    whatsapp: Annotated[str | None, Field(max_length=50, pattern=PATTERNS['phone_number'])] = None
    instagram: Annotated[str | None, Field(max_length=255, pattern=PATTERNS['instagram'])] = None
    telegram: Annotated[str | None, Field(max_length=255, pattern=PATTERNS['telegram'])] = None
    youtube: Annotated[str | None, Field(max_length=255, pattern=PATTERNS['youtube'])] = None
    website: Annotated[str | None, Field(max_length=255, pattern=PATTERNS['website'])] = None
    vk: Annotated[str | None, Field(max_length=255, pattern=PATTERNS['vk'])] = None
    about: Annotated[str | None, Field(max_length=255)] = None

    @field_validator('first_name', 'last_name', mode='after')
    @classmethod
    def capitalize(cls, v: str) -> str | None:
        return v.capitalize() if v else None


class SocialRead(BaseSocial):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUID4 | str
    user: UserInfoSchema
    avatar: str
    created: datetime
    updated: datetime

    @computed_field  # type: ignore[misc]
    @cached_property
    def url(self) -> str:
        return get_url('socials', uuid=self.uuid)


class SocialCreate(BaseSocial):
    user_id: UUIDstr


class SocialUpdatePartial(BaseSocial):
    pass


class SocialUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    avatar: str
    first_name: Annotated[str, Field(min_length=2, max_length=50, pattern=PATTERNS['name'])]
    last_name: Annotated[str, Field(min_length=2, max_length=50, pattern=PATTERNS['name'])]
    phone_number: Annotated[str, Field(max_length=50, pattern=PATTERNS['phone_number'])]
    viber: Annotated[str, Field(max_length=50, pattern=PATTERNS['phone_number'])]
    whatsapp: Annotated[str, Field(max_length=50, pattern=PATTERNS['phone_number'])]
    instagram: Annotated[str, Field(max_length=255, pattern=PATTERNS['instagram'])]
    telegram: Annotated[str, Field(max_length=255, pattern=PATTERNS['telegram'])]
    youtube: Annotated[str, Field(max_length=255, pattern=PATTERNS['youtube'])]
    website: Annotated[str, Field(max_length=255, pattern=PATTERNS['website'])]
    vk: Annotated[str, Field(max_length=255, pattern=PATTERNS['vk'])]
    about: Annotated[str, Field(max_length=255)]


class SocialAdminUpdatePartial(SocialUpdatePartial):
    pass


class SocialAdminUpdate(SocialUpdate):
    pass


class SocialFilter(BaseFilter):
    first_name: str | None = None
    first_name__ilike: str | None = None
    first_name__like: str | None = None
    first_name__neq: str | None = None
    first_name__in: list[str] | None = None
    first_name__nin: list[str] | None = None
    last_name: str | None = None
    last_name__ilike: str | None = None
    last_name__like: str | None = None
    last_name__neq: str | None = None
    last_name__in: list[str] | None = None
    last_name__nin: list[str] | None = None

    class Constants(BaseFilter.Constants):
        model = SocialMedia
        search_model_fields = ['first_name', 'last_name', 'uuid']
