import asyncpg
import re
from fastapi import Request, HTTPException
from app.core.config import settings

_pool: asyncpg.Pool | None = None

# Tenant IDs are always UUIDs minted by us (never raw user input), but we
# validate the shape anyway before interpolating into SQL — defense in depth.
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

async def init_db_pool():
    global _pool
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
    )


async def close_db_pool():
    if _pool:
        await _pool.close()


async def get_login_db():
    async with _pool.acquire() as conn:
        await conn.execute("SET ROLE app_login_role")
        try:
            yield conn
        finally:
            await conn.execute("RESET ROLE")


async def get_tenant_db(request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant context on request")

    if not _UUID_RE.match(str(tenant_id)):
        raise HTTPException(status_code=400, detail="Malformed tenant context")

    async with _pool.acquire() as conn:
        # set_config with is_local=true scopes the setting to this transaction
        # only, so connections returned to the pool don't leak tenant context
        # into the next request that happens to grab the same connection.
        await conn.execute(
            "SELECT set_config('app.current_tenant', $1, false)", str(tenant_id)
        )
        try:
            yield conn
        finally:
            await conn.execute("SELECT set_config('app.current_tenant', '', false)")
