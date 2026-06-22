from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from src.models.db_models import APIUsage
from datetime import datetime
from typing import Tuple,List
from src.utils.logger import get_logger

_logger= get_logger(__name__)

async def get_total_and_error_counts(tenant_id: str, period_start: datetime, db: AsyncSession) -> Tuple[int, int]:
    """
    Returns (total_requests, error_requests) for the given tenant and period_start.
    Error requests are those with status_code >= 400.
    """
    try:
        _logger.info("fetching total and error counts from db")

        stmt = (
            select(
                func.count().label("total"),
                func.sum(case((APIUsage.status_code >= 400, 1), else_=0)).label("errors"),
            )
            .where((APIUsage.tenant_id == tenant_id) & (APIUsage.recorded_at >= period_start))
        )

        res = await db.execute(stmt)
        row = res.one()
        total = int(row.total or 0)
        errors = int(row.errors or 0)
        return total, errors

    except Exception as e:
        _logger.error(f"Error occured {e}")
        raise e


async def get_usage_by_endpoint(tenant_id: str, period_start: datetime, db: AsyncSession) -> List[dict]:
    """
    Returns a list of dicts with `endpoint` and `count` for the given tenant
    and period_start, ordered by count descending.
    """
    try:
        _logger.info("fetching usage by endpoint from db")

        stmt = (
            select(APIUsage.endpoint, func.count().label("count"))
            .where((APIUsage.tenant_id == tenant_id) & (APIUsage.recorded_at >= period_start))
            .group_by(APIUsage.endpoint)
            .order_by(func.count().desc())
        )

        res = await db.execute(stmt)
        rows = res.all()
        return [{"endpoint": r.endpoint, "count": int(r.count or 0)} for r in rows]

    except Exception as e:
        _logger.error(f"Error occured {e}")
        raise e


async def insert_api_usage_record(tenant_id: str, endpoint: str, status_code: int, db: AsyncSession) -> None:
    """Persist an API usage row using SQLAlchemy AsyncSession."""
    usage = APIUsage(tenant_id=tenant_id, endpoint=endpoint, status_code=status_code)
    db.add(usage)
    await db.commit()