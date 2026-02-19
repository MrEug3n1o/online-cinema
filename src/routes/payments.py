from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional
from decimal import Decimal
from src.database import get_db
from src.models import (
    User, Order, OrderItem, OrderStatus, Payment, PaymentItem, PaymentStatus,
    Purchase, PurchaseItem, Movie
)
from src.schemas.payment import (
    StripePaymentCreate, PaymentResponse, PaymentListItem, PaginatedPayments,
    StripePaymentIntentResponse, StripePaymentConfirm, PaymentStatusResponse,
    Message, PaymentItemResponse
)
from src.dependencies import get_current_active_user
from src.services.stripe import StripeService
from src.email import send_email
from src.config import get_settings

router = APIRouter(prefix="/payments", tags=["Payments"])
settings = get_settings()


def send_payment_confirmation_email(user_email: str, payment_id: int, amount: Decimal):
    """Send payment confirmation email"""
    subject = f"Payment Confirmation - Online Cinema"
    body = f"""
    <html>
        <body>
            <h2>Payment Successful!</h2>
            <p>Your payment has been processed successfully.</p>
            <p><strong>Payment ID:</strong> {payment_id}</p>
            <p><strong>Amount:</strong> ${amount}</p>
            <p>Thank you for your purchase!</p>
            <br>
            <p>Best regards,<br>Online Cinema Team</p>
        </body>
    </html>
    """
    send_email(user_email, subject, body)


@router.post("/create-intent", response_model=StripePaymentIntentResponse)
def create_payment_intent(
        payment_data: StripePaymentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Create a Stripe Payment Intent for an order
    Step 1: Initialize payment with Stripe
    """
    # Get order
    order = db.query(Order).options(
        joinedload(Order.items)
    ).filter(
        Order.id == payment_data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order status is {order.status.value}, cannot create payment"
        )

    existing_payment = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.SUCCESSFUL])
    ).first()

    if existing_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already exists for this order"
        )

    total_amount = order.total_amount
    if not total_amount or total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order amount"
        )

    try:
        intent = StripeService.create_payment_intent(
            amount=total_amount,
            metadata={
                'order_id': order.id,
                'user_id': current_user.id,
                'user_email': current_user.email
            }
        )

        payment = Payment(
            user_id=current_user.id,
            order_id=order.id,
            status=PaymentStatus.PENDING,
            amount=total_amount,
            external_payment_id=intent['id'],
            payment_method='stripe'
        )
        db.add(payment)
        db.flush()

        for order_item in order.items:
            payment_item = PaymentItem(
                payment_id=payment.id,
                order_item_id=order_item.id,
                price_at_payment=order_item.price_at_order
            )
            db.add(payment_item)

        db.commit()
        db.refresh(payment)

        return StripePaymentIntentResponse(
            payment_intent_id=intent['id'],
            client_secret=intent['client_secret'],
            status=intent['status'],
            amount=total_amount,
            message="Payment intent created successfully"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )


@router.post("/confirm", response_model=PaymentStatusResponse)
def confirm_payment(
        confirm_data: StripePaymentConfirm,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Confirm payment after client-side Stripe confirmation
    Step 2: Verify and finalize payment
    """
    # Find payment by external ID
    payment = db.query(Payment).filter(
        Payment.external_payment_id == confirm_data.payment_intent_id,
        Payment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status == PaymentStatus.SUCCESSFUL:
        return PaymentStatusResponse(
            payment_id=payment.id,
            status=payment.status,
            external_payment_id=payment.external_payment_id,
            message="Payment already confirmed"
        )

    try:
        intent = StripeService.retrieve_payment_intent(confirm_data.payment_intent_id)

        if intent['status'] == 'succeeded':
            payment.status = PaymentStatus.SUCCESSFUL

            order = payment.order
            order.status = OrderStatus.PAID
            order.payment_gateway_reference = payment.external_payment_id

            purchase = Purchase(
                user_id=current_user.id,
                total_amount=payment.amount,
                payment_method='stripe',
                payment_status='completed',
                transaction_id=payment.external_payment_id
            )
            db.add(purchase)
            db.flush()

            for payment_item in payment.items:
                order_item = payment_item.order_item
                purchase_item = PurchaseItem(
                    purchase_id=purchase.id,
                    movie_id=order_item.movie_id,
                    user_id=current_user.id,
                    price_at_purchase=payment_item.price_at_payment
                )
                db.add(purchase_item)

            db.commit()

            background_tasks.add_task(
                send_payment_confirmation_email,
                current_user.email,
                payment.id,
                payment.amount
            )

            return PaymentStatusResponse(
                payment_id=payment.id,
                status=payment.status,
                external_payment_id=payment.external_payment_id,
                message="Payment confirmed successfully. Confirmation email sent."
            )

        elif intent['status'] in ['processing', 'requires_action']:
            return PaymentStatusResponse(
                payment_id=payment.id,
                status=PaymentStatus.PENDING,
                external_payment_id=payment.external_payment_id,
                message=f"Payment is {intent['status']}. Please complete required actions."
            )

        else:
            payment.status = PaymentStatus.FAILED
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed with status: {intent['status']}. Please try a different payment method."
            )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}"
        )


@router.get("", response_model=PaginatedPayments)
def get_payments(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        status: Optional[PaymentStatus] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's payment history"""
    query = db.query(Payment).filter(Payment.user_id == current_user.id)

    if status:
        query = query.filter(Payment.status == status)

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
def get_payment(
        payment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get detailed payment information"""
    payment = db.query(Payment).options(
        joinedload(Payment.items)
    ).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

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


@router.post("/{payment_id}/cancel", response_model=Message)
def cancel_payment(
        payment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Cancel a pending payment"""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending payments can be cancelled"
        )

    try:
        if payment.external_payment_id:
            StripeService.cancel_payment_intent(payment.external_payment_id)

        payment.status = PaymentStatus.CANCELED
        db.commit()

        return Message(
            message="Payment cancelled successfully",
            details={"payment_id": payment.id}
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel payment: {str(e)}"
        )
