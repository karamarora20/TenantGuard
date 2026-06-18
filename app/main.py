from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.connection import init_db_pool, close_db_pool
from app.api import auth, orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield
    await close_db_pool()


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    description="Tenant isolation via PostgreSQL RLS, JWT auth, RBAC.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(orders.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
