from src.models.db_models import Tenant, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.utils.logger import get_logger
from sqlalchemy.exc import NoResultFound

logger = get_logger(__name__)

async def get_tenant_plan(tenant_id: str,db: AsyncSession) -> str:
    """Fetches the tenant's plan from the database. This is used in the rate limiting logic to determine which tier of rate limits to apply."""
    logger.info(f"Fetching plan for tenant_id: {tenant_id}")
    try:
        
            stmt = select(Tenant.plan).where(Tenant.id == tenant_id)
            result = await db.execute(stmt)
            plan_row = result.scalar_one_or_none()
            if plan_row:
                logger.info(f"Tenant {tenant_id} has plan: {plan_row}")
                return plan_row
            else:
                logger.warning(f"No tenant found with id: {tenant_id}. Defaulting to 'free' plan.")
                return "free"
    except Exception as e:
        logger.error(f"Error fetching tenant plan for tenant_id {tenant_id}: {e}")
        return "free"  # default to free on error to avoid blocking requests

async def get_tenant_by_email(db: AsyncSession, tenant_email: str) -> Tenant | None:

    logger.info(f"Looking up tenant by email: {tenant_email}")
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.tenant_email == tenant_email)
        )
        tenant = result.scalar_one_or_none()
        return tenant
    except NoResultFound:
        logger.info(f"No tenant found with email: {tenant_email}")
        tenant = None
    except Exception as e:
        logger.error(f"Error occurred while looking up tenant: {e}")
        tenant = None
    

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    logger.info(f"Looking up user by email: {email}")
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return user
    except NoResultFound:
        logger.info(f"No user found with email: {email}")
        user = None
    except Exception as e:
        logger.error(f"Error occurred while looking up user: {e}")
        user = None
    
    
async def create_tenant(db: AsyncSession, tenant_email: str, plan: str=None) -> Tenant: # utility function, not currently used in the flow  
    try:
        new_tenant = Tenant(tenant_email=tenant_email, plan=plan)
        db.add(new_tenant)
        await db.commit()
        await db.refresh(new_tenant)
        return new_tenant
    except Exception as e:
        logger.error(f"Error occurred while creating tenant: {e}")
        raise

async def create_user(db: AsyncSession, email: str, hashed_password: str, tenant: str) -> User:
    try:
        tenant_obj = await get_tenant_by_email(db, tenant)
        if not tenant_obj:
            logger.error(f"Tenant not found for email: {tenant}")
            raise ValueError("Tenant not found")
        await db.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant',
                :tenant_id,
                false
            )
            """
        ),
        {"tenant_id": str(tenant_obj.id)},
    )
        new_user = User(email=email, hashed_password=hashed_password, tenant_id=tenant_obj.id)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except Exception as e:
        logger.error(f"Error occurred while creating user: {e}")
        raise
