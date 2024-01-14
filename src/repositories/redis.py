import time
from typing import Awaitable, Callable

import aioredis
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Request, Response, status, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import UUID4
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import config


def create_redis() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool.from_url(config.REDIS_DSN, decode_responses=False)


pool = create_redis()


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=pool)


class RedisRepository:
    def __init__(self, redis: aioredis.Redis = Depends(get_redis)) -> None:
        self.redis = redis
        self.fernet = Fernet(config.SECRET_KEY)
        self.redis_hash = config.REDIS_HASH

    def encrypt_token(self, token: str) -> bytes:
        return self.fernet.encrypt(token.encode('utf-8'))

    def decrypt_token(self, token: bytes) -> str:
        return self.fernet.decrypt(token).decode('utf-8')

    async def send_token(self, token: str, uuid: UUID4 | str) -> None:
        encrypted_token = self.encrypt_token(token)
        await self.redis.hset(self.redis_hash, str(uuid), encrypted_token)

    async def get_token(self, uuid: UUID4 | str) -> str | None:
        token = await self.redis.hget(self.redis_hash, str(uuid))
        return self.decrypt_token(token) if token else None

    async def delete_token(self, uuid: UUID4 | str) -> None:
        await self.redis.hdel(self.redis_hash, str(uuid))


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
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f'Redis error: {e!r}',
                ) from e
        return results[1] > max_requests


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
    ) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.max_requests = config.MAX_REQUESTS
        self.window = config.MAX_REQUESTS_WINDOW

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        host = request.client.host if request.client else '127.0.0.1'
        key = f'rate_limit:{host}:{request.url.path}'
        if await self.rate_limiter.is_rate_limited(key, self.max_requests, self.window):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=jsonable_encoder(
                    {
                        'code': status.HTTP_429_TOO_MANY_REQUESTS,
                        'message': 'Too many requests',
                    }
                ),
            )
        response = await call_next(request)
        return response
