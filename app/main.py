from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.routes import auth, wallet, transactions
from app.core.exceptions import PayFlowError
from app.core.redis import connect_redis, disconnect_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_redis()
    yield
    await disconnect_redis()


app = FastAPI(title="PayFlow", version="1.0.0", lifespan=lifespan)


@app.exception_handler(PayFlowError)
async def payflow_error_handler(request: Request, exc: PayFlowError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(transactions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}