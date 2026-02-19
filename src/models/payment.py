from sqlalchemy import Column, Integer, ForeignKey, DateTime, DECIMAL, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PENDING = "pending"  # Added for payment processing
    FAILED = "failed"  # Added for failed payments


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.SUCCESSFUL, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    external_payment_id = Column(String, nullable=True, unique=True, index=True)  # Stripe payment intent ID
    payment_method = Column(String, nullable=True)  # e.g., "stripe", "card"

    user = relationship("User", back_populates="payments")
    order = relationship("Order", back_populates="payments")
    items = relationship("PaymentItem", back_populates="payment", cascade="all, delete-orphan")


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    order_item_id = Column(Integer, ForeignKey('order_items.id', ondelete='RESTRICT'), nullable=False)
    price_at_payment = Column(DECIMAL(10, 2), nullable=False)

    payment = relationship("Payment", back_populates="items")
    order_item = relationship("OrderItem")
