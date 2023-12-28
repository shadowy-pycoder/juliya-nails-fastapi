from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api import router_v1


app = FastAPI(title='JuliyaNails', description='Beauty master service', version='1.0.0')
app.include_router(router_v1)


@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder({"code": 500, "msg": "Internal Server Error"})
    )
