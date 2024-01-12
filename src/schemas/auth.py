from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    EmailStr,
    Field,
    model_validator,
)

from src.schemas.base import UUIDstr
from src.utils import check_password_strength


class UserPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUIDstr

    @field_validator('uuid')
    @classmethod
    def stringify_token(cls, v: UUID) -> str:
        return str(v)


class VerifyUserRequest(BaseModel):
    token: str


class EmailRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: Annotated[str, Field(exclude=True)]
    email: Annotated[EmailStr, Field(max_length=100, exclude=True)]
    password: Annotated[str, Field(min_length=8)]
    confirm_password: Annotated[str, Field(exclude=True, min_length=8)]

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        check_password_strength(v)
        return v

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'ResetRequest':
        pw = self.password
        cpw = self.confirm_password
        if pw != cpw:
            raise ValueError('Passwords do not match')
        return self


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_name: str = 'bearer'
