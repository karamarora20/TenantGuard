import http

from pydantic import BaseModel, EmailStr
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Any


class LoginRequest(BaseModel):
    email: EmailStr
    password: str




class OrderCreate(BaseModel):
    customer_name: str
    amount: Decimal

class HTTPResponse(BaseModel):
    data: Any = None
    message: str = "Success"
    status: http.HTTPStatus = http.HTTPStatus.OK

class OrderResponse(BaseModel):
    id: UUID
    customer_name: str
    amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class EndpointCount(BaseModel):
    endpoint: str
    count: int


class UsageSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    plan: str
    monthly_limit: int
    total_requests: int
    remaining_requests: int
    in_overage: bool
    overage_requests: int
    overage_charge_usd: float
    overage_allowed: bool
    error_count: int
    error_rate_pct: float
    by_endpoint: list[EndpointCount] = []


class PlanTierInfo(BaseModel):
    monthly_limit: int
    overage_rate_per_1000: float


class BillingSummary(UsageSummary):
    plan_comparison: dict[str, PlanTierInfo]
