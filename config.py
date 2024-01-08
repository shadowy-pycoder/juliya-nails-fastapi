from pathlib import Path
from typing import Any

from fastapi_mail import FastMail, ConnectionConfig
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

with open('config.yaml') as fstream:
    config_yaml = yaml.safe_load(fstream)


class Config(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file='.env', env_file_encoding='utf-8')
    APP_NAME: str = 'JuliyaNails'
    DESCRIPTION: str = 'Beauty master service'
    VERSION: str = '1.0.0'
    SERVER_HOST: str = '127.0.0.1'
    SERVER_PORT: int = 8000
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRATION: int = 3600
    JWT_REFRESH_EXPIRATION: int = 3600 * 24 * 7
    REDIS_HOST: str
    REDIS_PORT: int
    # REDIS_DB: int
    # REDIS_PASSWORD: str
    REDIS_HASH: str
    SECRET_KEY: bytes
    SECRET_SALT: bytes
    CONFIRM_EXPIRATION: int = 3600
    ROOT_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: str = 'static/images/'
    DEFAULT_AVATAR: str = 'default.jpg'
    IMAGE_SIZE: int = 2097152
    ACCEPTED_FILE_TYPES: list[str] = ["image/png", "image/jpeg", "image/jpg", "png", "jpeg", "jpg"]
    CACHE_EXPIRE: int = 60
    MAX_REQUESTS: int = 5
    MAX_REQUESTS_WINDOW: int = 60
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    MAIL_DEBUG: bool
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    TEMPLATE_FOLDER: Path = Path(__file__).resolve().parent / 'templates'
    USE_CREDENTIALS: bool
    FRONTEND_HOST: str = 'http://127.0.0.1:8001'
    LOGGING: dict[str, Any] = config_yaml['logging']


config = Config()

conf = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_STARTTLS=config.MAIL_STARTTLS,
    MAIL_SSL_TLS=config.MAIL_SSL_TLS,
    MAIL_DEBUG=config.MAIL_DEBUG,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_FROM_NAME=config.MAIL_FROM_NAME,
    TEMPLATE_FOLDER=config.TEMPLATE_FOLDER,
    USE_CREDENTIALS=config.USE_CREDENTIALS,
)

fm = FastMail(conf)
