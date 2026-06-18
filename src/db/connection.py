from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import text
from src.config.settings import settings
from fastapi import Request,HTTPException
from uuid import UUID

engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://...
    pool_size=10,
    max_overflow=20,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_login_db():
    async with AsyncSessionLocal() as session:

        await session.execute(
            text("SET ROLE app_login_role")
        )

        try:
            yield session

        finally:
            await session.execute(
                text("RESET ROLE")
            )


async def get_tenant_db(request: Request):

    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="No tenant context"
        )

    try:
        UUID(str(tenant_id))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Malformed tenant id"
        )

    async with AsyncSessionLocal() as session:

        await session.execute(
            text(
                """
                SELECT set_config(
                    'app.current_tenant',
                    :tenant_id,
                    true
                )
                """
            ),
            {"tenant_id": str(tenant_id)}
        )

        try:
            yield session

        finally:
            await session.execute(
                text(
                    """
                    SELECT set_config(
                        'app.current_tenant',
                        '',
                        false
                    )
                    """
                )
            )
