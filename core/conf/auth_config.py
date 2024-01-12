from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRATION: int = 3600
    JWT_REFRESH_EXPIRATION: int = 3600 * 24 * 7
    SECRET_KEY: bytes
    SECRET_SALT: bytes
    CONFIRM_EXPIRATION: int = 3600
