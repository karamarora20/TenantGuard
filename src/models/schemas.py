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
