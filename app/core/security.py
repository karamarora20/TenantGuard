from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(tenant_id: str, user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def auth_middleware(request: Request, token: str = Depends(oauth2_scheme)):
    try:
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


def require_role(allowed_roles: list[str]):
    """Dependency factory for per-route authorization.

    Usage:
        @app.delete("/orders/{id}")
        async def delete_order(..., _: None = Depends(require_role(["admin"]))):
            ...

    This is intentionally separate from tenant isolation (RLS). RLS decides
    whether tenant A can see tenant B's rows — a hard security boundary.
    This decides whether a 'viewer' inside tenant A can delete an order —
    a business-logic boundary. Conflating the two gets messy fast once you
    have more than two roles.
    """

    def checker(request: Request):
        user_role = getattr(request.state, "user_role", None)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user_role}' is not permitted to perform this action",
            )

    return checker
