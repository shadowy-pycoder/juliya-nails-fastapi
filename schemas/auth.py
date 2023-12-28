from uuid import UUID
from typing import Annotated
from pydantic import BaseModel, ConfigDict, validator, UUID4, AfterValidator


class UserPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUID4 | Annotated[str, AfterValidator(lambda x: UUID(x, version=4))]

    @validator('uuid')
    def stringify_token(cls, value: UUID) -> str:
        return str(value)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_name: str = 'bearer'
