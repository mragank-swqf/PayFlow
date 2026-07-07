from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.routes import auth, wallet, transactions
from app.core.redis import connect_redis, disconnect_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_redis()
    yield
    await disconnect_redis()

app = FastAPI(title="PayFlow", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(transactions.router)

@app.get("/health")
async def health():
    return {"status": "ok"}