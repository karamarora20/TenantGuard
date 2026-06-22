from datetime import datetime, timezone
from src.config.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession
from src.service import api_usage_service

# Monthly request limits per plan — separate from rate limits (per-minute).
# Rate limits = burst protection. Monthly limits = billing thresholds.



async def record_request(
    tenant_id: str,
    endpoint: str,
    status_code: int,
    db:AsyncSession,  # asyncpg pool passed in to avoid circular imports
):
    """
    Fire-and-forget usage log. Called via BackgroundTask so the response
    has already been sent to the client before this runs.
    """
    await api_usage_service.insert_api_usage_record(tenant_id, endpoint, status_code, db)


async def get_usage_summary(tenant_id: str, plan: str, db:AsyncSession) -> dict:
    """
    Aggregates usage for the current calendar month and computes billing.
    """
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total requests this billing period
    total,errors=await api_usage_service.get_total_and_error_counts(tenant_id,period_start,db)
    # Breakdown by endpoint — useful for the demo UI
    by_endpoint = await api_usage_service.get_usage_by_endpoint(tenant_id,period_start,db)


    monthly_limit = settings.MONTHLY_LIMITS.get(plan, settings.MONTHLY_LIMITS["free"])
    overage = max(0, total - monthly_limit)
    overage_rate = settings.OVERAGE_RATE_PER_1000.get(plan, 0)
    overage_charge = (overage / 1000) * overage_rate

    return {
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "plan": plan,
        "monthly_limit": monthly_limit,
        "total_requests": total,
        "remaining_requests": max(0, monthly_limit - total),
        "in_overage": overage > 0,
        "overage_requests": overage,
        "overage_charge_usd": round(overage_charge, 4),
        "overage_allowed": plan != "free",
        "error_count": errors,
        "error_rate_pct": round((errors / total * 100), 2) if total > 0 else 0,
        "by_endpoint": [
            {"endpoint": r["endpoint"], "count": r["count"]} for r in by_endpoint
        ],
    }
