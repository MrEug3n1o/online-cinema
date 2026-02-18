from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from src.models.order import OrderStatus


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    movie_id: int
    price_at_order: Decimal
    movie: dict  # Will contain movie details

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Request to create order from cart"""
    pass  # No additional fields needed, uses cart items


class OrderResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    status: OrderStatus
    total_amount: Optional[Decimal]
    payment_gateway_reference: Optional[str]
    items: List[OrderItemResponse]
    items_count: int

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: int
    created_at: datetime
    status: OrderStatus
    total_amount: Optional[Decimal]
    items_count: int

    class Config:
        from_attributes = True


class PaginatedOrders(BaseModel):
    items: List[OrderListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentRequest(BaseModel):
    payment_method: str = Field(..., description="Payment method: credit_card, paypal, etc.")
    card_number: Optional[str] = Field(None, description="Card number (for credit_card)")


class PaymentResponse(BaseModel):
    order_id: int
    payment_gateway_reference: str
    redirect_url: Optional[str] = None
    status: str
    message: str


class OrderCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for cancellation")


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    payment_gateway_reference: Optional[str] = None


class RefundRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)
    refund_amount: Optional[Decimal] = Field(None, description="Partial refund amount")


class RefundResponse(BaseModel):
    order_id: int
    refund_status: str
    refund_amount: Decimal
    message: str


class OrderValidationResult(BaseModel):
    valid: bool
    message: str
    excluded_movies: List[dict] = []
    total_amount: Optional[Decimal] = None
    pending_orders: List[int] = []


class OrderFilters(BaseModel):
    user_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class Message(BaseModel):
    message: str
    details: Optional[dict] = None
