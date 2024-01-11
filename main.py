import logging.config

from aioredis import Redis
from fastapi import FastAPI, Request, status, Depends
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api import router_v1
from config import config
from database import get_async_session, AsyncSession
from repositories.redis import get_redis, RateLimitMiddleware

app = FastAPI(
    title=config.APP_NAME,
    description=config.DESCRIPTION,
    version=config.VERSION,
)
app.include_router(
    router_v1,
    responses={
        status.HTTP_404_NOT_FOUND: {'description': 'Not found'},
        status.HTTP_401_UNAUTHORIZED: {'description': 'Unauthorized'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Too many requests'},
    },
)
add_pagination(app)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            {
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'Internal Server Error',
            },
        ),
    )


@app.on_event('startup')
async def startup() -> None:
    FastAPICache.init(
        RedisBackend(get_redis()),
        prefix='fastapi-cache',
        expire=config.CACHE_EXPIRE,
    )
    logging.config.dictConfig(config.LOGGING)


@app.get(
    '/up',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    include_in_schema=False,
)
async def healthcheck(
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    await redis.ping()
    await session.execute(text('SELECT 1'))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                'code': status.HTTP_200_OK,
                'message': 'Healthy',
            },
        ),
    )
