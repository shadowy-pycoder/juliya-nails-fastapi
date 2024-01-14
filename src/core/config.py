from fastapi_mail import FastMail, ConnectionConfig
from pydantic_settings import SettingsConfigDict

from .conf import AuthConfig, DBConfig, EmailConfig, RedisConfig, ServerConfig


class Config(AuthConfig, DBConfig, EmailConfig, RedisConfig, ServerConfig):
    model_config = SettingsConfigDict(
        case_sensitive=True, env_file='.env', env_file_encoding='utf-8'
    )


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
    TEMPLATE_FOLDER=config.ROOT_DIR / config.TEMPLATE_FOLDER,
    USE_CREDENTIALS=config.USE_CREDENTIALS,
    SUPPRESS_SEND=config.SUPPRESS_SEND,
)
fm = FastMail(conf)
