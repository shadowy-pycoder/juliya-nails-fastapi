import aioredis
from cryptography.fernet import Fernet
from fastapi import Depends
from pydantic import UUID4

from config import config


def create_redis() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool(
        host=config.redis_host,
        port=config.redis_port,
        # db=config.redis_db,
        # password=config.redis_password,
        decode_responses=False,
    )


pool = create_redis()


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=pool)


class RedisService:
    def __init__(self, redis: aioredis.Redis = Depends(get_redis)) -> None:
        self.redis = redis
        self.fernet = Fernet(config.encrypt_key)

    def encrypt_token(self, token: str) -> bytes:
        return self.fernet.encrypt(token.encode('utf-8'))

    def decrypt_token(self, token: bytes) -> str:
        return self.fernet.decrypt(token).decode('utf-8')

    async def send_token(self, token: str, uuid: UUID4 | str) -> None:
        encrypted_token = self.encrypt_token(token)
        await self.redis.hset(config.redis_hash, str(uuid), encrypted_token)

    async def get_token(self, uuid: UUID4 | str) -> str | None:
        token = await self.redis.hget(config.redis_hash, str(uuid))
        return self.decrypt_token(token) if token else None

    async def delete_token(self, uuid: UUID4 | str) -> None:
        await self.redis.hdel(config.redis_hash, str(uuid))
