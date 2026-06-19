from sqlalchemy import (Column, String, Integer, DateTime,ForeignKey, Numeric,Integer,BigInteger,CheckConstraint,UniqueConstraint,Index,text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func


Base= declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True,server_default=text("gen_random_uuid()"))
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, server_default=text("'member'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_user_tenant_email",
        ),
        CheckConstraint(
            "role IN ('admin', 'member', 'viewer')",
            name="ck_user_role",
        ),
    )
    orders = relationship(
        "Order",
        back_populates="creator"
    )
    tenant= relationship("Tenant", back_populates="users")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(UUID(as_uuid=True), primary_key=True,server_default=text("gen_random_uuid()"))
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    customer_name = Column(String, nullable=False)
    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )
    status = Column(String, default='pending')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','paid','cancelled')",
            name="ck_order_status",
        ),
    )
    tenant= relationship("Tenant", back_populates="orders")
    creator= relationship("User", back_populates="orders")

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    name = Column(String, nullable=False)
    
    plan = Column(
        String,
        nullable=False,
        server_default=text("'free'")
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    tenant_email=   Column(String, nullable=False)  

    __table_args__ = (
        CheckConstraint(
            "plan IN ('free', 'pro', 'enterprise')",
            name="ck_tenant_plan",
        ),
    )
    users= relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    orders= relationship("Order", back_populates="tenant", cascade="all, delete-orphan")

class APIUsage(Base):
    __tablename__ = 'api_usage'
    id = Column(BigInteger, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
Index(
    "idx_api_usage_tenant_time",
    APIUsage.tenant_id,
    APIUsage.recorded_at,
)

Index(
    "idx_users_tenant",
    User.tenant_id,
)

Index(
    "idx_orders_tenant",
    Order.tenant_id,
)