from fastapi import APIRouter, HTTPException,Depends,Request
from src.utils.middleware import auth_middleware
from src.db.connection import get_tenant_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request
from src.config.security import require_role
from src.config.settings import settings
from src.utils.api_usage_util import get_usage_summary
from src.models.schemas import UsageSummary, BillingSummary
from src.utils.middleware import get_tenant_plan
from src.db.connection import get_tenant_db


router = APIRouter(prefix='/usage',
                         tags=['usage'],
                         dependencies=[Depends(auth_middleware)]  # every route below requires a valid JWT
)


@router.get("", response_model=UsageSummary)
async def usage(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    tenant_id = request.state.tenant_id
    plan = await get_tenant_plan(tenant_id)
    summary = await get_usage_summary(tenant_id, plan, db)
    return summary


@router.get("/summary", response_model=BillingSummary)
async def billing_summary(
    request: Request,
    _: None = Depends(require_role(["admin"])),  # billing details = admin only,
    db:AsyncSession=Depends(get_tenant_db)
):
    tenant_id = request.state.tenant_id
    plan = await get_tenant_plan(tenant_id)
    summary = await get_usage_summary(tenant_id, plan, db)

    return {
        **summary,
        "plan_comparison": {
            tier: {
                "monthly_limit": settings.MONTHLY_LIMITS[tier],
                "overage_rate_per_1000": settings.OVERAGE_RATE_PER_1000[tier],
            }
            for tier in ["free", "pro", "enterprise"]
        },
    }
