import time
from typing import Awaitable, Callable

import aioredis
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Request, Response, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import UUID4
from starlette.middleware.base import BaseHTTPMiddleware


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


class RedisRepository:
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


class RateLimiter:
    def __init__(self) -> None:
        self.redis = get_redis()

    async def is_rate_limited(self, key: str, max_requests: int, window: int) -> bool:
        current = int(time.time())
        window_start = current - window
        async with self.redis.pipeline() as pipe:
            try:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {str(current): current})
                pipe.expire(key, window)
                results = await pipe.execute()
            except aioredis.RedisError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Redis error: {e!r}") from e
        return results[1] > max_requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
    ) -> None:
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.max_requests = config.max_requests
        self.window = config.max_requests_window

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        host = request.client.host if request.client else '127.0.0.1'
        key = f"rate_limit:{host}:{request.url.path}"
        if await self.rate_limiter.is_rate_limited(key, self.max_requests, self.window):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=jsonable_encoder({'code': 429, 'msg': 'Too many requests'}),
            )
        response = await call_next(request)
        return response
