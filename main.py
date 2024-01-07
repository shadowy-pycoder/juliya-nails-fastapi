from fastapi import FastAPI, Request, status
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.responses import JSONResponse

from api import router_v1
from config import config
from repositories.redis import get_redis, RateLimitMiddleware

app = FastAPI(
    title=config.app_name,
    description=config.description,
    version=config.version,
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
        expire=config.cache_expire,
    )
