import stripe
from typing import Optional, Dict, Any
from decimal import Decimal
from src.config import get_settings

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for handling Stripe payment operations"""

    @staticmethod
    def create_payment_intent(
            amount: Decimal,
            currency: str = "usd",
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent

        Args:
            amount: Amount in dollars (will be converted to cents)
            currency: Currency code (default: usd)
            metadata: Additional metadata to attach

        Returns:
            Payment Intent object
        """
        amount_cents = int(amount * 100)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            return intent
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    @staticmethod
    def retrieve_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """Retrieve a Payment Intent by ID"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    @staticmethod
    def confirm_payment_intent(
            payment_intent_id: str,
            payment_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Confirm a Payment Intent"""
        try:
            params = {}
            if payment_method:
                params['payment_method'] = payment_method

            return stripe.PaymentIntent.confirm(payment_intent_id, **params)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    @staticmethod
    def cancel_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """Cancel a Payment Intent"""
        try:
            return stripe.PaymentIntent.cancel(payment_intent_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    @staticmethod
    def create_refund(
            payment_intent_id: str,
            amount: Optional[Decimal] = None,
            reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment

        Args:
            payment_intent_id: The payment intent to refund
            amount: Amount to refund in dollars (None for full refund)
            reason: Reason for refund

        Returns:
            Refund object
        """
        try:
            params = {'payment_intent': payment_intent_id}

            if amount:
                params['amount'] = int(amount * 100)

            if reason:
                params['reason'] = reason

            return stripe.Refund.create(**params)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    @staticmethod
    def construct_webhook_event(
            payload: bytes,
            sig_header: str,
            webhook_secret: str
    ) -> stripe.Event:
        """
        Construct and verify a webhook event

        Args:
            payload: Raw request body
            sig_header: Stripe signature header
            webhook_secret: Webhook secret for verification

        Returns:
            Verified Stripe Event
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except ValueError as e:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise Exception("Invalid signature")

    @staticmethod
    def get_payment_method(payment_method_id: str) -> Dict[str, Any]:
        """Retrieve payment method details"""
        try:
            return stripe.PaymentMethod.retrieve(payment_method_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
