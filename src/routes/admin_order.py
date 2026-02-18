from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
from typing import Optional
from datetime import datetime
from src.database import get_db
from src.models import User, Order, OrderItem, OrderStatus, Movie
from src.schemas.order import (
    OrderResponse, PaginatedOrders, OrderListItem,
    OrderStatusUpdate, Message, RefundRequest, RefundResponse
)
from src.dependencies import get_admin_user, get_moderator_user

router = APIRouter(prefix="/admin/orders", tags=["Admin - Order Management"])


def _build_movie_dict(movie: Movie) -> dict:
    """Build movie dictionary for response"""
    return {
        'id': movie.id,
        'name': movie.name,
        'year': movie.year,
        'price': movie.price,
        'genres': [genre.name for genre in movie.genres]
    }


@router.get("", response_model=PaginatedOrders)
def get_all_orders(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        user_id: Optional[int] = None,
        status: Optional[OrderStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """
    Get all orders with filters (Admin only)
    Filters: user_id, status, date range
    """
    query = db.query(Order)

    if user_id:
        query = query.filter(Order.user_id == user_id)

    if status:
        query = query.filter(Order.status == status)

    if date_from:
        query = query.filter(Order.created_at >= date_from)

    if date_to:
        query = query.filter(Order.created_at <= date_to)

    query = query.order_by(desc(Order.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    orders = query.offset(offset).limit(page_size).all()

    order_list = []
    for order in orders:
        items_count = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).count()

        order_list.append(OrderListItem(
            id=order.id,
            created_at=order.created_at,
            status=order.status,
            total_amount=order.total_amount,
            items_count=items_count
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedOrders(
        items=order_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Get detailed order information (Admin only)"""
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.movie).joinedload(Movie.genres)
    ).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    items_response = []
    for item in order.items:
        movie_dict = _build_movie_dict(item.movie)
        items_response.append({
            'id': item.id,
            'order_id': item.order_id,
            'movie_id': item.movie_id,
            'price_at_order': item.price_at_order,
            'movie': movie_dict
        })

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        status=order.status,
        total_amount=order.total_amount,
        payment_gateway_reference=order.payment_gateway_reference,
        items=items_response,
        items_count=len(items_response)
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
        order_id: int,
        status_update: OrderStatusUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Update order status (Admin only)"""
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.movie).joinedload(Movie.genres)
    ).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    order.status = status_update.status
    if status_update.payment_gateway_reference:
        order.payment_gateway_reference = status_update.payment_gateway_reference

    db.commit()
    db.refresh(order)

    # Build response
    items_response = []
    for item in order.items:
        movie_dict = _build_movie_dict(item.movie)
        items_response.append({
            'id': item.id,
            'order_id': item.order_id,
            'movie_id': item.movie_id,
            'price_at_order': item.price_at_order,
            'movie': movie_dict
        })

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        status=order.status,
        total_amount=order.total_amount,
        payment_gateway_reference=order.payment_gateway_reference,
        items=items_response,
        items_count=len(items_response)
    )


@router.post("/{order_id}/refund", response_model=RefundResponse)
def process_refund(
        order_id: int,
        refund_data: RefundRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """
    Process refund for paid order (Admin only)
    - Can do full or partial refund
    - Changes order status to CANCELED
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paid orders can be refunded"
        )

    refund_amount = refund_data.refund_amount if refund_data.refund_amount else order.total_amount

    if refund_amount > order.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount cannot exceed order total"
        )

    order.status = OrderStatus.CANCELED
    db.commit()

    return RefundResponse(
        order_id=order.id,
        refund_status="processed",
        refund_amount=refund_amount,
        message=f"Refund of ${refund_amount} processed successfully. Reason: {refund_data.reason}"
    )


@router.get("/statistics/summary", response_model=Message)
def get_order_statistics(
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Get order statistics (Moderator+)"""
    query = db.query(Order)

    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    total_orders = query.count()
    pending_orders = query.filter(Order.status == OrderStatus.PENDING).count()
    paid_orders = query.filter(Order.status == OrderStatus.PAID).count()
    canceled_orders = query.filter(Order.status == OrderStatus.CANCELED).count()

    from sqlalchemy import func
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.status == OrderStatus.PAID
    ).scalar() or 0

    return Message(
        message="Order statistics",
        details={
            "total_orders": total_orders,
            "pending": pending_orders,
            "paid": paid_orders,
            "canceled": canceled_orders,
            "total_revenue": str(total_revenue)
        }
    )
