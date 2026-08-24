from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum
from app.core.database import Base
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    product_id = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)