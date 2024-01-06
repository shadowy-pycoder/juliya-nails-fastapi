from __future__ import annotations
from datetime import datetime
from functools import cached_property
import re
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    UUID4,
    AfterValidator,
    Field,
    field_validator,
    model_validator,
    computed_field,
)

from models.users import User
from schemas.base import BaseFilter, UUIDstr
from utils import PATTERNS, get_url


class BaseUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator('password', check_fields=False)
    @classmethod
    def validate_password(cls, v: str) -> str:
        message = 'Password should contain at least '
        error_log = []
        errors = {
            '1 digit': re.search(r'\d', v) is None,
            '1 uppercase letter': re.search(r'[A-Z]', v) is None,
            '1 lowercase letter': re.search(r'[a-z]', v) is None,
            '1 special character': re.search(r'\W', v) is None,
        }
        for err_msg, error in errors.items():
            if error:
                error_log.append(err_msg)
        if error_log:
            raise ValueError(message + ', '.join(err for err in error_log))
        return v


class UserRead(BaseUser):
    uuid: UUIDstr
    email: EmailStr
    username: str
    created: datetime
    updated: datetime
    confirmed: bool
    confirmed_on: datetime | None
    active: bool
    admin: bool

    @computed_field  # type: ignore[misc]
    @cached_property
    def entries(self) -> str:
        return get_url('users', 'get_user_entries', uuid=self.uuid)

    @computed_field  # type: ignore[misc]
    @cached_property
    def posts(self) -> str:
        return get_url('users', 'get_user_posts', uuid=self.uuid)

    @computed_field  # type: ignore[misc]
    @cached_property
    def socials(self) -> str:
        return get_url('users', 'get_user_socials', uuid=self.uuid)


class UserCreate(BaseUser):
    email: Annotated[EmailStr, Field(max_length=100)]
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=PATTERNS['username'])]
    password: Annotated[str, Field(min_length=8)]
    confirm_password: Annotated[str, Field(exclude=True, min_length=8)]

    @model_validator(mode='after')
    def check_passwords_match(self) -> UserCreate:
        pw = self.password
        cpw = self.confirm_password
        if pw != cpw:
            raise ValueError('Passwords do not match')
        return self


class UserUpdate(UserCreate):
    pass


class UserUpdatePartial(BaseUser):
    email: Annotated[EmailStr | None, Field(max_length=100)] = None
    username: Annotated[str | None, Field(min_length=2, max_length=20, pattern=PATTERNS['username'])] = None
    password: Annotated[str | None, Field(exclude=True, min_length=8)] = None
    confirm_password: Annotated[str | None, Field(exclude=True, min_length=8)] = None

    @model_validator(mode='after')
    def check_passwords_match(self) -> UserUpdatePartial:
        pw = self.password
        cpw = self.confirm_password
        if pw is not None and cpw is not None and pw != cpw:
            raise ValueError('Passwords do not match')
        elif pw is None and cpw is not None:
            raise ValueError('Password field is missing')
        elif pw is not None and cpw is None:
            raise ValueError('Confirm password field is missing')
        return self


class UserAdminUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: Annotated[EmailStr, Field(max_length=100)]
    username: Annotated[str, Field(min_length=2, max_length=20)]
    password: Annotated[str, Field(exclude=True, min_length=8)]
    created: datetime
    confirmed: bool
    confirmed_on: datetime
    active: bool
    admin: bool


class UserAdminUpdatePartial(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: Annotated[EmailStr | None, Field(max_length=100)] = None
    username: Annotated[str | None, Field(min_length=2, max_length=20)] = None
    password: Annotated[str | None, Field(exclude=True, min_length=8)] = None
    created: datetime | None = None
    confirmed: bool | None = None
    confirmed_on: datetime | None = None
    active: bool | None = None
    admin: bool | None = None


class UserInfoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: Annotated[UUID4, AfterValidator(lambda x: str(x))] | str
    username: str

    @computed_field  # type: ignore[misc]
    @cached_property
    def url(self) -> str:
        return get_url('users', uuid=self.uuid)


class UserFilter(BaseFilter):
    email: str | None = None
    username: str | None = None
    username__ilike: str | None = None
    username__like: str | None = None
    username__neq: str | None = None
    username__in: list[str] | None = None
    username__nin: list[str] | None = None
    confirmed: bool | None = None
    confirmed_on: datetime | None = None
    confirmed_on__gt: datetime | None = None
    confirmed_on__gte: datetime | None = None
    confirmed_on__lt: datetime | None = None
    confirmed_on__lte: datetime | None = None
    active: bool | None = None
    admin: bool | None = None

    class Constants(BaseFilter.Constants):
        model = User
        search_model_fields = ['username', 'uuid']
