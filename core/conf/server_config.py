from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings
import yaml


def get_logging_config(path: Path) -> dict[str, Any]:
    with open(path) as fstream:
        config_yaml = yaml.safe_load(fstream)
    return config_yaml['logging']


class ServerConfig(BaseSettings):
    APP_NAME: str = 'JuliyaNails'
    DESCRIPTION: str = 'Beauty master service'
    VERSION: str = '1.0.0'
    OPENAPI_URL: str | None = '/openapi.json'
    DOCS_URL: str | None = '/docs'
    REDOC_URL: str | None = '/redoc'
    SERVER_HOST: str = '127.0.0.1'
    SERVER_PORT: int = 8000
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: str = 'static/images/'
    DEFAULT_AVATAR: str = 'default.jpg'
    IMAGE_SIZE: int = 2097152
    ACCEPTED_FILE_TYPES: list[str] = ['image/png', 'image/jpeg', 'image/jpg', 'png', 'jpeg', 'jpg']
    CACHE_EXPIRE: int = 60
    MAX_REQUESTS: int = 5
    MAX_REQUESTS_WINDOW: int = 60
    TEMPLATE_FOLDER: str = 'templates'
    FRONTEND_HOST: str = 'http://127.0.0.1:8001'
    LOGGING: dict[str, Any] = get_logging_config(ROOT_DIR / 'core/conf/logging_config.yaml')
    ORIGINS: list[str] = ['http://127.0.0.1:8001']
