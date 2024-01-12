from pydantic_settings import BaseSettings


class EmailConfig(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    MAIL_DEBUG: bool
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    USE_CREDENTIALS: bool
