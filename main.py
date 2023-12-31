from fastapi import FastAPI, Request, status
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.responses import JSONResponse

from api import router_v1

from services.redis import get_redis


app = FastAPI(title='JuliyaNails', description='Beauty master service', version='1.0.0')
app.include_router(router_v1)
add_pagination(app)


@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder({"code": 500, "msg": "Internal Server Error"})
    )


@app.on_event("startup")
async def startup() -> None:
    FastAPICache.init(RedisBackend(get_redis()), prefix="fastapi-cache", expire=60)
