from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    server_host: str = '127.0.0.1'
    server_port: int = 8000
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_pass: str
    database_url: str
    jwt_secret_key: str
    jwt_refresh_secret_key: str
    jwt_algorithm: str = 'HS256'
    jwt_expiration: int = 3600
    jwt_refresh_expiration: int = 3600 * 24 * 7
    redis_host: str
    redis_port: int
    # redis_db: int
    # redis_password: str
    redis_hash: str
    encrypt_key: bytes


settings = Settings()