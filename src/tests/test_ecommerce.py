import pytest
from fastapi import status


class TestShoppingCart:
    """Test shopping cart functionality"""

    def test_get_empty_cart(self, client, auth_headers):
        """Test getting empty cart"""
        response = client.get("/cart", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items_count"] == 0
        assert float(data["total_amount"]) == 0.0

    def test_add_to_cart(self, client, auth_headers, sample_movie_data):
        """Test adding movie to cart"""
        movie_id = sample_movie_data["movie"].id
        response = client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["movie_id"] == movie_id

    def test_add_duplicate_to_cart(self, client, auth_headers, sample_movie_data):
        """Test adding same movie twice"""
        movie_id = sample_movie_data["movie"].id

        # Add first time
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Try to add again
        response = client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already in your cart" in response.json()["detail"].lower()

    def test_remove_from_cart(self, client, auth_headers, sample_movie_data):
        """Test removing movie from cart"""
        movie_id = sample_movie_data["movie"].id

        # Add to cart
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Remove from cart
        response = client.delete(
            f"/cart/items/{movie_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_clear_cart(self, client, auth_headers, sample_movie_data):
        """Test clearing entire cart"""
        movie_id = sample_movie_data["movie"].id

        # Add to cart
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Clear cart
        response = client.delete("/cart/clear", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify cart is empty
        cart_response = client.get("/cart", headers=auth_headers)
        assert cart_response.json()["items_count"] == 0

    def test_cart_validation(self, client, auth_headers, sample_movie_data):
        """Test cart validation"""
        movie_id = sample_movie_data["movie"].id

        # Add to cart
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Validate cart
        response = client.post("/cart/validate", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


class TestOrders:
    """Test order creation and management"""

    def test_create_order_from_cart(self, client, auth_headers, sample_movie_data):
        """Test creating order from cart"""
        movie_id = sample_movie_data["movie"].id

        # Add to cart
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Create order
        response = client.post("/orders", headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "pending"
        assert len(data["items"]) > 0

    def test_create_order_empty_cart(self, client, auth_headers):
        """Test creating order with empty cart"""
        response = client.post("/orders", headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "empty" in response.json()["detail"].lower()

    def test_get_orders(self, client, auth_headers, sample_movie_data):
        """Test getting order history"""
        movie_id = sample_movie_data["movie"].id

        # Create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        client.post("/orders", headers=auth_headers)

        # Get orders
        response = client.get("/orders", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] > 0

    def test_get_order_details(self, client, auth_headers, sample_movie_data):
        """Test getting order details"""
        movie_id = sample_movie_data["movie"].id

        # Create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        order_response = client.post("/orders", headers=auth_headers)
        order_id = order_response.json()["id"]

        # Get order details
        response = client.get(f"/orders/{order_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == order_id

    def test_cancel_pending_order(self, client, auth_headers, sample_movie_data):
        """Test cancelling pending order"""
        movie_id = sample_movie_data["movie"].id

        # Create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        order_response = client.post("/orders", headers=auth_headers)
        order_id = order_response.json()["id"]

        # Cancel order
        response = client.post(
            f"/orders/{order_id}/cancel",
            headers=auth_headers,
            json={"reason": "Changed my mind"}
        )
        assert response.status_code == status.HTTP_200_OK


class TestPayments:
    """Test payment processing"""

    def test_create_payment_intent(self, client, auth_headers, sample_movie_data):
        """Test creating payment intent"""
        movie_id = sample_movie_data["movie"].id

        # Create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        order_response = client.post("/orders", headers=auth_headers)
        order_id = order_response.json()["id"]

        # Create payment intent
        response = client.post(
            "/payments/create-intent",
            headers=auth_headers,
            json={"order_id": order_id}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "payment_intent_id" in data
        assert "client_secret" in data

    def test_confirm_payment(self, client, auth_headers, sample_movie_data):
        """Test confirming payment"""
        movie_id = sample_movie_data["movie"].id

        # Create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        order_response = client.post("/orders", headers=auth_headers)
        order_id = order_response.json()["id"]

        # Create payment intent
        intent_response = client.post(
            "/payments/create-intent",
            headers=auth_headers,
            json={"order_id": order_id}
        )
        payment_intent_id = intent_response.json()["payment_intent_id"]

        # Confirm payment
        response = client.post(
            "/payments/confirm",
            headers=auth_headers,
            json={"payment_intent_id": payment_intent_id}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_payment_history(self, client, auth_headers, sample_movie_data):
        """Test getting payment history"""
        response = client.get("/payments", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data


class TestPurchases:
    """Test purchase tracking"""

    def test_get_purchased_movies(self, client, auth_headers):
        """Test getting list of purchased movies"""
        response = client.get("/purchases/movies/list", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_check_movie_purchased(self, client, auth_headers, sample_movie_data):
        """Test checking if movie is purchased"""
        movie_id = sample_movie_data["movie"].id
        response = client.get(
            f"/purchases/check/{movie_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK


class TestEndToEndPurchaseFlow:
    """Test complete purchase workflow"""

    def test_complete_purchase_flow(self, client, auth_headers, sample_movie_data):
        """Test full flow: cart → order → payment → purchase"""
        movie_id = sample_movie_data["movie"].id

        # Step 1: Add to cart
        cart_response = client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        assert cart_response.status_code == status.HTTP_201_CREATED

        # Step 2: Validate cart
        validate_response = client.post(
            "/cart/validate",
            headers=auth_headers
        )
        assert validate_response.json()["valid"] is True

        # Step 3: Create order
        order_response = client.post("/orders", headers=auth_headers)
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        # Step 4: Create payment intent
        intent_response = client.post(
            "/payments/create-intent",
            headers=auth_headers,
            json={"order_id": order_id}
        )
        assert intent_response.status_code == status.HTTP_200_OK
        payment_intent_id = intent_response.json()["payment_intent_id"]

        # Step 5: Confirm payment
        confirm_response = client.post(
            "/payments/confirm",
            headers=auth_headers,
            json={"payment_intent_id": payment_intent_id}
        )
        assert confirm_response.status_code == status.HTTP_200_OK

        # Step 6: Verify purchase
        check_response = client.get(
            f"/purchases/check/{movie_id}",
            headers=auth_headers
        )
        assert check_response.json()["message"] == "purchased"

        # Step 7: Verify cart is cleared
        cart_check = client.get("/cart", headers=auth_headers)
        assert cart_check.json()["items_count"] == 0

    def test_cannot_purchase_twice(self, client, auth_headers, sample_movie_data, db_session):
        """Test that user cannot purchase same movie twice"""
        from src.models import Purchase, PurchaseItem

        movie_id = sample_movie_data["movie"].id
        user_id = 1  # test_user id

        # Create a purchase manually
        purchase = Purchase(
            user_id=user_id,
            total_amount=9.99,
            payment_method="test",
            payment_status="completed",
            transaction_id="test_123"
        )
        db_session.add(purchase)
        db_session.flush()

        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            movie_id=movie_id,
            user_id=user_id,
            price_at_purchase=9.99
        )
        db_session.add(purchase_item)
        db_session.commit()

        response = client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already purchased" in response.json()["detail"].lower()
