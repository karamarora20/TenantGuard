from pydantic import BaseModel, EmailStr
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrderCreate(BaseModel):
    customer_name: str
    amount: Decimal


class OrderResponse(BaseModel):
    id: UUID
    customer_name: str
    amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
