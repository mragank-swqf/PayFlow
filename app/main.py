from fastapi import FastAPI
from app.api.v1.routes import auth

app = FastAPI(title="PayFlow", version="1.0.0")
app.include_router(auth.router)

@app.get("/health")
async def health():
    return {"status": "ok"}