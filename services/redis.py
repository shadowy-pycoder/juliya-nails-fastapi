import aioredis
from cryptography.fernet import Fernet
from fastapi import Depends
from pydantic import UUID4

from settings import settings


def create_redis() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool(
        host=settings.redis_host,
        port=settings.redis_port,
        # db=settings.redis_db,
        # password=settings.redis_password,
        decode_responses=False,
    )


pool = create_redis()


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=pool)


class RedisService:
    def __init__(self, redis: aioredis.Redis = Depends(get_redis)) -> None:
        self.redis = redis
        self.fernet = Fernet(settings.encrypt_key)

    def encrypt_token(self, token: str) -> bytes:
        return self.fernet.encrypt(token.encode('utf-8'))

    def decrypt_token(self, token: bytes) -> str:
        return self.fernet.decrypt(token).decode('utf-8')

    async def send_token(self, token: str, uuid: UUID4 | str) -> None:
        encrypted_token = self.encrypt_token(token)
        await self.redis.hset(settings.redis_hash, str(uuid), encrypted_token)

    async def get_token(self, uuid: UUID4 | str) -> str | None:
        token = await self.redis.hget(settings.redis_hash, str(uuid))
        return self.decrypt_token(token) if token else None

    async def delete_token(self, uuid: UUID4 | str) -> None:
        await self.redis.hdel(settings.redis_hash, str(uuid))
