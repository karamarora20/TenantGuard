from src.models.db_models import Order
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.schemas import OrderCreate
from src.utils.logger import get_logger
from sqlalchemy.exc import ProgrammingError

logger = get_logger(__name__)

async def get_orders(db: AsyncSession) -> list[Order]:
    try:
        logger.info("Executing get_orders query")
        stmt = select(Order).order_by(Order.created_at.desc())
        result = await db.execute(stmt)
        res= [r[0] for r in result.fetchall()]
        return res
    except ProgrammingError as PE:
        logger.error("Database error occurred for wrong tenant context or malformed query")
        return []
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        # Log the error and re-raise or return an empty list depending on your error handling strategy
        raise

async def create_order(db: AsyncSession, order: OrderCreate, user_id: str,tenant_id: str=None) -> Order:
    try:
        logger.info(f"Executing create_order for customer: {order.customer_name}")
        new_order = Order(
        tenant_id=tenant_id,  
        created_by=user_id, 
        customer_name=order.customer_name,
        amount=order.amount,
    )
        db.add(new_order)
        return new_order
    except Exception as e:
        logger.error(f"Error inserting order: {e}")
        # Log the error and re-raise or return an empty list depending on your error handling strategy
        raise