from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator

from schemas.base import UUIDstr


class UserPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUIDstr

    @field_validator('uuid')
    @classmethod
    def stringify_token(cls, v: UUID) -> str:
        return str(v)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_name: str = 'bearer'
