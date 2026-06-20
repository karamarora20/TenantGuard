from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from src.db.redis import close_redis, init_redis
from src.routers import auth, orders
from src.utils.middleware import rate_limit_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    description="Tenant isolation via PostgreSQL RLS, JWT auth, RBAC.",
    lifespan=lifespan
)

app.include_router(auth.router)
app.include_router(orders.router)

app.middleware("http")(rate_limit_middleware)

@app.get("/health")
async def health():
    return {"status": "ok"}
