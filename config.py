from pathlib import Path

from fastapi_mail import FastMail, ConnectionConfig
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    app_name: str = 'JuliyaNails'
    description: str = 'Beauty master service'
    version: str = '1.0.0'
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
    secret_key: bytes
    secret_salt: bytes
    confirm_expiration: int = 3600
    root_dir: Path = Path(__file__).resolve().parent
    upload_dir: str = 'static/images/'
    default_avatar: str = 'default.jpg'
    image_size: int = 2097152
    accepted_file_types: list[str] = ["image/png", "image/jpeg", "image/jpg", "png", "jpeg", "jpg"]
    cache_expire: int = 60
    max_requests: int = 5
    max_requests_window: int = 60
    mail_username: str
    mail_password: str
    mail_port: int
    mail_server: str
    mail_starttls: bool
    mail_ssl_tls: bool
    mail_debug: bool
    mail_from: str
    mail_from_name: str
    template_folder: Path = Path(__file__).resolve().parent / 'templates'
    use_credentials: bool
    frontend_host: str = 'http://127.0.0.1:8001'


config = Config()

conf = ConnectionConfig(
    MAIL_USERNAME=config.mail_username,
    MAIL_PASSWORD=config.mail_password,
    MAIL_PORT=config.mail_port,
    MAIL_SERVER=config.mail_server,
    MAIL_STARTTLS=config.mail_starttls,
    MAIL_SSL_TLS=config.mail_ssl_tls,
    MAIL_DEBUG=config.mail_debug,
    MAIL_FROM=config.mail_from,
    MAIL_FROM_NAME=config.mail_from_name,
    TEMPLATE_FOLDER=config.template_folder,
    USE_CREDENTIALS=config.use_credentials,
)

fm = FastMail(conf)
