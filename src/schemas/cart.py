from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from src.schemas.movie import MovieListResponse


class CartItemAdd(BaseModel):
    movie_id: int


class MovieInCart(BaseModel):
    id: int
    name: str
    year: int
    price: Decimal
    genres: List[str]

    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    movie_id: int
    added_at: datetime
    movie: MovieInCart

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    items: List[CartItemResponse]
    total_amount: Decimal
    items_count: int

    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    items_count: int
    total_amount: Decimal
    movies: List[MovieInCart]


class CheckoutRequest(BaseModel):
    payment_method: str = Field(..., description="Payment method: credit_card, paypal, etc.")


class PurchaseItemResponse(BaseModel):
    id: int
    movie_id: int
    price_at_purchase: Decimal
    movie: MovieInCart

    class Config:
        from_attributes = True


class PurchaseResponse(BaseModel):
    id: int
    user_id: int
    total_amount: Decimal
    payment_method: str
    payment_status: str
    transaction_id: Optional[str]
    created_at: datetime
    items: List[PurchaseItemResponse]

    class Config:
        from_attributes = True


class PurchaseListItem(BaseModel):
    id: int
    total_amount: Decimal
    payment_method: str
    payment_status: str
    created_at: datetime
    items_count: int

    class Config:
        from_attributes = True


class PaginatedPurchases(BaseModel):
    items: List[PurchaseListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PurchasedMovieResponse(BaseModel):
    movie: MovieInCart
    purchased_at: datetime
    price_paid: Decimal

    class Config:
        from_attributes = True


class UserCartSummary(BaseModel):
    user_id: int
    user_email: str
    items_count: int
    total_amount: Decimal
    last_updated: datetime


class Message(BaseModel):
    message: str
    details: Optional[dict] = None
