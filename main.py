from fastapi import FastAPI

from src.routers import auth, orders


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    description="Tenant isolation via PostgreSQL RLS, JWT auth, RBAC.",
)

app.include_router(auth.router)
app.include_router(orders.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
