from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Payment, PaymentStatus, Order, OrderStatus, Purchase, PurchaseItem
from src.services.stripe import StripeService
from src.config import get_settings
import logging

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
        request: Request,
        stripe_signature: str = Header(None, alias="stripe-signature"),
        db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events
    Events handled:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - payment_intent.canceled
    - charge.refunded
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )

    payload = await request.body()

    try:
        event = StripeService.construct_webhook_event(
            payload,
            stripe_signature,
            settings.STRIPE_WEBHOOK_SECRET
        )

        logger.info(f"Received Stripe webhook: {event['type']}")

        if event['type'] == 'payment_intent.succeeded':
            handle_payment_success(event['data']['object'], db)

        elif event['type'] == 'payment_intent.payment_failed':
            handle_payment_failed(event['data']['object'], db)

        elif event['type'] == 'payment_intent.canceled':
            handle_payment_canceled(event['data']['object'], db)

        elif event['type'] == 'charge.refunded':
            handle_charge_refunded(event['data']['object'], db)

        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


def handle_payment_success(payment_intent, db: Session):
    """Handle successful payment"""
    payment_intent_id = payment_intent['id']

    payment = db.query(Payment).filter(
        Payment.external_payment_id == payment_intent_id
    ).first()

    if not payment:
        logger.warning(f"Payment not found for intent: {payment_intent_id}")
        return

    if payment.status == PaymentStatus.SUCCESSFUL:
        logger.info(f"Payment {payment.id} already marked as successful")
        return

    payment.status = PaymentStatus.SUCCESSFUL

    order = payment.order
    if order:
        order.status = OrderStatus.PAID
        order.payment_gateway_reference = payment_intent_id

    existing_purchase = db.query(Purchase).filter(
        Purchase.transaction_id == payment_intent_id
    ).first()

    if not existing_purchase:
        purchase = Purchase(
            user_id=payment.user_id,
            total_amount=payment.amount,
            payment_method='stripe',
            payment_status='completed',
            transaction_id=payment_intent_id
        )
        db.add(purchase)
        db.flush()

        for payment_item in payment.items:
            order_item = payment_item.order_item
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                movie_id=order_item.movie_id,
                user_id=payment.user_id,
                price_at_purchase=payment_item.price_at_payment
            )
            db.add(purchase_item)

    db.commit()
    logger.info(f"Payment {payment.id} marked as successful")


def handle_payment_failed(payment_intent, db: Session):
    """Handle failed payment"""
    payment_intent_id = payment_intent['id']

    payment = db.query(Payment).filter(
        Payment.external_payment_id == payment_intent_id
    ).first()

    if not payment:
        logger.warning(f"Payment not found for intent: {payment_intent_id}")
        return

    payment.status = PaymentStatus.FAILED
    db.commit()
    logger.info(f"Payment {payment.id} marked as failed")


def handle_payment_canceled(payment_intent, db: Session):
    """Handle canceled payment"""
    payment_intent_id = payment_intent['id']

    payment = db.query(Payment).filter(
        Payment.external_payment_id == payment_intent_id
    ).first()

    if not payment:
        logger.warning(f"Payment not found for intent: {payment_intent_id}")
        return

    payment.status = PaymentStatus.CANCELED
    db.commit()
    logger.info(f"Payment {payment.id} marked as canceled")


def handle_charge_refunded(charge, db: Session):
    """Handle refunded charge"""
    payment_intent_id = charge.get('payment_intent')

    if not payment_intent_id:
        logger.warning("No payment_intent in refund event")
        return

    payment = db.query(Payment).filter(
        Payment.external_payment_id == payment_intent_id
    ).first()

    if not payment:
        logger.warning(f"Payment not found for intent: {payment_intent_id}")
        return

    payment.status = PaymentStatus.REFUNDED

    order = payment.order
    if order:
        order.status = OrderStatus.CANCELED

    db.commit()
    logger.info(f"Payment {payment.id} marked as refunded")
