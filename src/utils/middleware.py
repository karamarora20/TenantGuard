
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from src.service import auth_service
from src.config.settings import settings
from src.utils.rate_limiter import is_rate_limited
from src.db.redis import get_redis
from src.db.connection import AsyncSessionLocal
from src.config.settings import settings
import logging
from fastapi.security import  HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from src.config.security import security
logger = logging.getLogger(__name__)




async def get_tenant_plan(tenant_id: str) -> str:
    """
    Fetches the tenant's plan — free, pro, or enterprise.
    Caches the result in Redis for 5 minutes to avoid a Postgres
    round-trip on every single request. Plan changes are eventually
    consistent (up to 5 min lag), which is fine for rate limiting.
    """
    redis = get_redis()
    cache_key = f"tenant_plan:{tenant_id}"

    cached = await redis.get(cache_key)
    if cached:
        return cached
    plan = "free"  # default to free if any errors occur

    async with AsyncSessionLocal() as session:
        plan = await auth_service.get_tenant_plan(tenant_id, db= session)

    await redis.set(cache_key, plan, ex=300)  # cache for 5 minutes
    return plan


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in settings.EXEMPT_PATHS:
        return await call_next(request)

    # Extract JWT without full verification — we just need the tenant_id claim.
    # Full verification happens in auth_middleware inside the route dependency.
    # Doing a full verify here would be redundant work on every request.
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return await call_next(request)

    token = auth_header.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return await call_next(request)
    except JWTError:
        # Invalid token — let auth_middleware handle the 401, not us
        return await call_next(request)

    plan = await get_tenant_plan(tenant_id)
    limited, retry_after = await is_rate_limited(tenant_id, plan)

    if limited:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "plan": plan,
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    return await call_next(request)




async def auth_middleware(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token=credentials.credentials
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    request.state.tenant_id = payload.get("tenant_id")
    request.state.user_id = payload.get("sub")
    request.state.user_role = payload.get("role")

    if not request.state.tenant_id or not request.state.user_role:
        raise HTTPException(status_code=401, detail="Malformed token claims")

