from src.models.db_models import Order
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.schemas import OrderCreate
from src.utils.logger import get_logger
from sqlalchemy.exc import ProgrammingError

_logger = get_logger(__name__)

async def get_orders(db: AsyncSession) -> list[Order]:
    try:
        _logger.info("Executing get_orders query")
        stmt = select(Order).order_by(Order.created_at.desc())
        result = await db.execute(stmt)
        orders = result.scalars().all()
        return orders
    except ProgrammingError as PE:
        _logger.error("Database error occurred for wrong tenant context or malformed query")
        return []
    except Exception as e:
        _logger.error(f"Error fetching orders: {e}")
        # Log the error and re-raise or return an empty list depending on your error handling strategy
        raise

async def create_order(db: AsyncSession, order: OrderCreate, user_id: str, tenant_id: str = None) -> Order:
    try:
        _logger.info(f"Executing create_order for customer: {order.customer_name}")

        if not user_id or not tenant_id:
            raise ValueError("Missing user_id or tenant_id for order creation")

        new_order = Order(
            tenant_id=tenant_id,
            created_by=user_id,
            customer_name=order.customer_name,
            amount=order.amount,
        )
        db.add(new_order)
        await db.flush()
        return new_order
    except Exception as e:
        _logger.error(f"Error inserting order: {e}")
        raise
async def delete_order(db: AsyncSession, order_id: str) -> bool:
    try:
        _logger.info(f"Executing delete order for order id {order_id}")
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order_obj = result.scalar_one_or_none()

        if order_obj is None:
            _logger.info(f"No order found for order id {order_id}")
            return False

        await db.delete(order_obj)
        return True
    except Exception as e:
        _logger.error(f"Delete failed for order id {order_id}: {e}")
        raise