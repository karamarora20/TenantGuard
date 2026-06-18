from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
import asyncpg

from src.db.connection import get_tenant_db
from src.config.security import auth_middleware, require_role
from src.models.schemas import OrderCreate, OrderResponse

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(auth_middleware)],  # every route below requires a valid JWT
)

@router.get("", response_model=List[OrderResponse])
async def list_orders(conn: asyncpg.Connection = Depends(get_tenant_db)):
    # No WHERE tenant_id = ... here on purpose — RLS adds it for us.
    rows = await conn.fetch(
        "SELECT id, customer_name, amount, status, created_at FROM orders ORDER BY created_at DESC"
    )
    return [OrderResponse(**dict(r)) for r in rows]


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order: OrderCreate,
    request: Request,
    conn: asyncpg.Connection = Depends(get_tenant_db),
):
    row = await conn.fetchrow(
        """
        INSERT INTO orders (tenant_id, created_by, customer_name, amount)
        VALUES (current_setting('src.current_tenant')::UUID, $1, $2, $3)
        RETURNING id, customer_name, amount, status, created_at
        """,
        request.state.user_id,
        order.customer_name,
        order.amount,
    )
    return OrderResponse(**dict(row))


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: str,
    conn: asyncpg.Connection = Depends(get_tenant_db),
    _: None = Depends(require_role(["admin"])),  # business rule, not a tenant boundary
):
    result = await conn.execute("DELETE FROM orders WHERE id = $1", order_id)
    if result == "DELETE 0":
        # Note: this also correctly returns 404 (not 403) if the order
        # belongs to a different tenant — RLS makes it invisible, so from
        # this tenant's perspective it simply doesn't exist. That's the
        # right behavior: we don't want to leak "it exists but isn't yours".
        raise HTTPException(status_code=404, detail="Order not found")
