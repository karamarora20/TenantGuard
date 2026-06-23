from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.service import order_service
from src.db.connection import get_tenant_db
from src.config.security import  require_role
from src.utils.middleware import auth_middleware
from src.models.schemas import OrderCreate, OrderResponse
from src.utils.logger import get_logger

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(auth_middleware)]  # every route below requires a valid JWT
)
_logger = get_logger(__name__)

@router.get("", response_model=List[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_tenant_db), request: Request = None):
    try:
        _logger.info("Fetching orders for tenant")
        orders = await order_service.get_orders(db)
        return [OrderResponse.from_orm(r) for r in orders]
    except Exception as e:
        _logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    try:
        _logger.info(f"Creating order for customer: {order.customer_name}")
        row = await order_service.create_order(db, order, request.state.user_id, request.state.tenant_id)
        await db.commit()
        return OrderResponse.from_orm(row)
    except Exception as e:
        _logger.error(f"Error creating order: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: None = Depends(require_role(["admin"])),  # business rule, not a tenant boundary
):
    try:
        _logger.info(f"Deleting order with id: {order_id}")
        result = await order_service.delete_order(db, order_id)
        if result:
            await db.commit()
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        db.rollback()
        _logger.error(f"Error deleting order: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
