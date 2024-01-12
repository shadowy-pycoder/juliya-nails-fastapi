from pydantic import field_validator, RedisDsn, ValidationInfo
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: str = '0'
    REDIS_PASSWORD: str = ''
    REDIS_HASH: str
    REDIS_DSN: str | None = None

    @field_validator('REDIS_DSN', mode='after')
    @classmethod
    def assemble_redis_dsn(cls, v: str | None, info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return RedisDsn.build(
            scheme='redis',
            password=info.data.get('REDIS_PASSWORD'),
            host=info.data['REDIS_HOST'],
            port=info.data.get('REDIS_PORT'),
            path=info.data.get('REDIS_DB'),
        ).unicode_string()
