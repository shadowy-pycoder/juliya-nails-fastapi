from uuid import UUID
from typing import Annotated
from pydantic import BaseModel, ConfigDict, field_validator, UUID4, AfterValidator


class UserPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUID4 | Annotated[str, AfterValidator(lambda x: UUID(x, version=4))]

    @field_validator('uuid')
    def stringify_token(cls, v: UUID) -> str:
        return str(v)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_name: str = 'bearer'
