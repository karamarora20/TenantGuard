from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import JSONResponse
from src.db.redis import close_redis, init_redis
from src.utils.middleware import rate_limit_middleware
from src.routers import auth_router, order_router,api_usage_router


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


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

app.include_router(auth_router.router)
app.include_router(order_router.router)
app.include_router(usage_router.router)

app.middleware("http")(rate_limit_middleware)

@app.get("/health")
async def health():
    return {"status": "ok"}
