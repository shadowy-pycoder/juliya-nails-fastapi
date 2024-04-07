import logging.config
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_pagination import add_pagination
from sqlalchemy import text

from redis.asyncio import Redis
from src.api import router_v1
from src.core.config import config
from src.database import AsyncSession, get_async_session
from src.repositories.redis import RateLimitMiddleware, get_redis


app = FastAPI(
    title=config.APP_NAME,
    description=config.DESCRIPTION,
    version=config.VERSION,
    openapi_url=config.OPENAPI_URL,
    docs_url=config.DOCS_URL,
    redoc_url=config.REDOC_URL,
)
app.include_router(
    router_v1,
    prefix='/api',
    responses={
        status.HTTP_404_NOT_FOUND: {'description': 'Not found'},
        status.HTTP_401_UNAUTHORIZED: {'description': 'Unauthorized'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Too many requests'},
    },
)
add_pagination(app)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


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
    app.state.start_time = datetime.now(tz=timezone.utc)


@app.get(
    '/',
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    include_in_schema=False,
)
def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(config.DOCS_URL)


@app.get(
    '/up',
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    include_in_schema=False,
)
async def healthcheck(
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
                'start': app.state.start_time,
                'uptime': datetime.now(tz=timezone.utc) - app.state.start_time,
            },
        ),
    )
