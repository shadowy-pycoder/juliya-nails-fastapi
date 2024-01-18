from pydantic import PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class DBConfig(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DSN: str | None = None

    @field_validator('POSTGRES_DSN', mode='after')
    @classmethod
    def assemble_postgres_dsn(cls, v: str | None, info: ValidationInfo) -> str | None:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            username=info.data.get('POSTGRES_USER'),
            password=info.data.get('POSTGRES_PASSWORD'),
            host=info.data.get('POSTGRES_HOST'),
            path=info.data.get('POSTGRES_DB'),
            port=info.data.get("POSTGRES_PORT"),
        ).unicode_string()
