from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime
from src.database import get_db
from src.models import User, Payment, PaymentItem, PaymentStatus, Order, OrderStatus
from src.schemas.payment import (
    PaymentResponse, PaginatedPayments, PaymentListItem,
    PaymentRefundRequest, PaymentRefundResponse, Message, PaymentItemResponse
)
from src.dependencies import get_admin_user, get_moderator_user
from src.services.stripe import StripeService

router = APIRouter(prefix="/admin/payments", tags=["Admin - Payment Management"])


@router.get("", response_model=PaginatedPayments)
def get_all_payments(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        user_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """
    Get all payments with filters (Admin only)
    Filters: user_id, order_id, status, date range
    """
    query = db.query(Payment)

    if user_id:
        query = query.filter(Payment.user_id == user_id)

    if order_id:
        query = query.filter(Payment.order_id == order_id)

    if status:
        query = query.filter(Payment.status == status)

    if date_from:
        query = query.filter(Payment.created_at >= date_from)

    if date_to:
        query = query.filter(Payment.created_at <= date_to)

    query = query.order_by(desc(Payment.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    payments = query.offset(offset).limit(page_size).all()

    payment_list = []
    for payment in payments:
        payment_list.append(PaymentListItem(
            id=payment.id,
            order_id=payment.order_id,
            created_at=payment.created_at,
            status=payment.status,
            amount=payment.amount,
            payment_method=payment.payment_method
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedPayments(
        items=payment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_detail(
        payment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Get detailed payment information (Admin only)"""
    payment = db.query(Payment).options(
        joinedload(Payment.items)
    ).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Build response
    items_response = []
    for item in payment.items:
        items_response.append(PaymentItemResponse(
            id=item.id,
            payment_id=item.payment_id,
            order_item_id=item.order_item_id,
            price_at_payment=item.price_at_payment
        ))

    return PaymentResponse(
        id=payment.id,
        user_id=payment.user_id,
        order_id=payment.order_id,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        status=payment.status,
        amount=payment.amount,
        external_payment_id=payment.external_payment_id,
        payment_method=payment.payment_method,
        items=items_response
    )


@router.post("/{payment_id}/refund", response_model=PaymentRefundResponse)
def refund_payment(
        payment_id: int,
        refund_data: PaymentRefundRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """
    Process refund for a successful payment (Admin only)
    - Can do full or partial refund
    - Changes payment status to REFUNDED
    - Updates order status to CANCELED
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status != PaymentStatus.SUCCESSFUL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only successful payments can be refunded"
        )

    refund_amount = refund_data.amount if refund_data.amount else payment.amount

    if refund_amount > payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount cannot exceed payment amount"
        )

    try:
        if payment.external_payment_id:
            refund = StripeService.create_refund(
                payment_intent_id=payment.external_payment_id,
                amount=refund_amount,
                reason=refund_data.reason
            )
            refund_id = refund['id']
        else:
            refund_id = f"MANUAL-REFUND-{payment.id}"

        payment.status = PaymentStatus.REFUNDED

        order = payment.order
        if order:
            order.status = OrderStatus.CANCELED

        db.commit()

        return PaymentRefundResponse(
            payment_id=payment.id,
            refund_id=refund_id,
            amount=refund_amount,
            status="processed",
            message=f"Refund of ${refund_amount} processed successfully. Reason: {refund_data.reason}"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


@router.get("/statistics/summary", response_model=Message)
def get_payment_statistics(
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """Get payment statistics (Moderator+)"""
    query = db.query(Payment)

    if date_from:
        query = query.filter(Payment.created_at >= date_from)
    if date_to:
        query = query.filter(Payment.created_at <= date_to)

    total_payments = query.count()
    successful = query.filter(Payment.status == PaymentStatus.SUCCESSFUL).count()
    pending = query.filter(Payment.status == PaymentStatus.PENDING).count()
    failed = query.filter(Payment.status == PaymentStatus.FAILED).count()
    canceled = query.filter(Payment.status == PaymentStatus.CANCELED).count()
    refunded = query.filter(Payment.status == PaymentStatus.REFUNDED).count()

    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.SUCCESSFUL
    ).scalar() or 0

    refunded_amount = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.REFUNDED
    ).scalar() or 0

    net_revenue = total_revenue - refunded_amount

    return Message(
        message="Payment statistics",
        details={
            "total_payments": total_payments,
            "successful": successful,
            "pending": pending,
            "failed": failed,
            "canceled": canceled,
            "refunded": refunded,
            "total_revenue": str(total_revenue),
            "refunded_amount": str(refunded_amount),
            "net_revenue": str(net_revenue)
        }
    )


@router.get("/user/{user_id}/history", response_model=PaginatedPayments)
def get_user_payment_history(
        user_id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Get payment history for specific user (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    query = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(desc(Payment.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    payments = query.offset(offset).limit(page_size).all()

    payment_list = []
    for payment in payments:
        payment_list.append(PaymentListItem(
            id=payment.id,
            order_id=payment.order_id,
            created_at=payment.created_at,
            status=payment.status,
            amount=payment.amount,
            payment_method=payment.payment_method
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedPayments(
        items=payment_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )