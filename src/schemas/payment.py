from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.models.payment_models import PaymentStatus


# Payment Item Schemas
class PaymentItemResponse(BaseModel):
    id: int
    payment_id: int
    order_item_id: int
    price_at_payment: Decimal

    class Config:
        from_attributes = True


# Payment Schemas
class StripePaymentCreate(BaseModel):
    order_id: int
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")
    return_url: Optional[str] = Field(None, description="URL to return to after payment")


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    order_id: int
    created_at: datetime
    updated_at: datetime
    status: PaymentStatus
    amount: Decimal
    external_payment_id: Optional[str]
    payment_method: Optional[str]
    items: List[PaymentItemResponse]

    class Config:
        from_attributes = True


class PaymentListItem(BaseModel):
    id: int
    order_id: int
    created_at: datetime
    status: PaymentStatus
    amount: Decimal
    payment_method: Optional[str]

    class Config:
        from_attributes = True


class PaginatedPayments(BaseModel):
    items: List[PaymentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class StripePaymentIntentResponse(BaseModel):
    payment_intent_id: str
    client_secret: str
    status: str
    amount: Decimal
    message: str


class StripePaymentConfirm(BaseModel):
    payment_intent_id: str


class PaymentStatusResponse(BaseModel):
    payment_id: int
    status: PaymentStatus
    external_payment_id: Optional[str]
    message: str


class PaymentRefundRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)
    amount: Optional[Decimal] = Field(None, description="Partial refund amount")


class PaymentRefundResponse(BaseModel):
    payment_id: int
    refund_id: str
    amount: Decimal
    status: str
    message: str


class PaymentFilters(BaseModel):
    user_id: Optional[int] = None
    order_id: Optional[int] = None
    status: Optional[PaymentStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class StripeWebhookEvent(BaseModel):
    type: str
    data: dict


class Message(BaseModel):
    message: str
    details: Optional[dict] = None
