import pytest
from fastapi import status


class TestAdminUserManagement:
    """Test admin user management endpoints"""

    def test_get_all_users(self, client, admin_headers):
        """Test getting all users as admin"""
        response = client.get("/admin/users", headers=admin_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_get_all_users_as_user(self, client, auth_headers):
        """Test getting all users as regular user (should fail)"""
        response = client.get("/admin/users", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_change_user_role(self, client, admin_headers, test_user):
        """Test changing user role"""
        response = client.patch(
            f"/admin/users/{test_user.id}/group",
            headers=admin_headers,
            json={"group_id": 2}  # Moderator
        )
        assert response.status_code == status.HTTP_200_OK

    def test_activate_user(self, client, admin_headers, test_user):
        """Test manually activating user"""
        response = client.patch(
            f"/admin/users/{test_user.id}/activate",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert response.status_code == status.HTTP_200_OK


class TestAdminOrderManagement:
    """Test admin order management"""

    def test_get_all_orders(self, client, admin_headers):
        """Test getting all orders as admin"""
        response = client.get("/admin/orders", headers=admin_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_filter_orders_by_status(self, client, admin_headers):
        """Test filtering orders by status"""
        response = client.get(
            "/admin/orders?status=pending",
            headers=admin_headers
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_order_statistics(self, client, admin_headers):
        """Test getting order statistics"""
        response = client.get(
            "/admin/orders/statistics/summary",
            headers=admin_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "details" in data


class TestAdminPaymentManagement:
    """Test admin payment management"""

    def test_get_all_payments(self, client, admin_headers):
        """Test getting all payments as admin"""
        response = client.get("/admin/payments", headers=admin_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_payment_statistics(self, client, admin_headers):
        """Test getting payment statistics"""
        response = client.get(
            "/admin/payments/statistics/summary",
            headers=admin_headers
        )
        assert response.status_code == status.HTTP_200_OK


class TestAdminCartManagement:
    """Test admin cart viewing"""

    def test_get_all_carts(self, client, admin_headers):
        """Test viewing all user carts"""
        response = client.get("/admin/carts", headers=admin_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_check_movie_in_carts(self, client, moderator_headers, sample_movie_data):
        """Test checking if movie is in any carts"""
        movie_id = sample_movie_data["movie"].id
        response = client.get(
            f"/admin/carts/movie/{movie_id}/usage",
            headers=moderator_headers
        )
        assert response.status_code == status.HTTP_200_OK


class TestDatabaseIntegration:
    """Test database operations and integrity"""

    def test_user_profile_creation(self, client, db_session):
        """Test that user profile is created with user"""
        from app.models import User, UserProfile, UserGroup, UserGroupEnum

        user_group = db_session.query(UserGroup).filter(
            UserGroup.name == UserGroupEnum.USER
        ).first()

        user = User(
            email="integration@test.com",
            hashed_password="hashed",
            is_active=True,
            group_id=user_group.id
        )
        db_session.add(user)
        db_session.flush()

        profile = UserProfile(user_id=user.id)
        db_session.add(profile)
        db_session.commit()

        assert user.profile is not None
        assert user.profile.user_id == user.id

    def test_movie_deletion_protection(self, client, moderator_headers, sample_movie_data, db_session):
        """Test that movies with purchases cannot be deleted"""
        from app.models import Purchase, PurchaseItem

        movie_id = sample_movie_data["movie"].id

        # Create a purchase
        purchase = Purchase(
            user_id=1,
            total_amount=9.99,
            payment_method="test",
            payment_status="completed",
            transaction_id="test_456"
        )
        db_session.add(purchase)
        db_session.flush()

        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            movie_id=movie_id,
            user_id=1,
            price_at_purchase=9.99
        )
        db_session.add(purchase_item)
        db_session.commit()

        # Try to delete movie
        response = client.delete(
            f"/moderator/movies/{movie_id}",
            headers=moderator_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "purchased" in response.json()["detail"].lower()

    def test_cascade_deletion(self, client, db_session, test_user):
        """Test that related records are deleted with user"""
        from app.models import User, UserProfile, Cart

        user_id = test_user.id

        # Create cart
        cart = Cart(user_id=user_id)
        db_session.add(cart)
        db_session.commit()

        # Delete user
        db_session.delete(test_user)
        db_session.commit()

        # Verify cart is also deleted
        cart_check = db_session.query(Cart).filter(Cart.user_id == user_id).first()
        assert cart_check is None


class TestAuthenticationIntegration:
    """Test authentication workflows"""

    def test_full_registration_workflow(self, client, db_session):
        """Test complete registration and activation workflow"""
        # Register
        register_response = client.post(
            "/auth/register",
            json={
                "email": "workflow@test.com",
                "password": "TestPass123!"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED

        # User should not be able to login before activation
        login_response = client.post(
            "/auth/login",
            json={
                "email": "workflow@test.com",
                "password": "TestPass123!"
            }
        )
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

        # Manually activate user for testing
        from app.models import User
        user = db_session.query(User).filter(
            User.email == "workflow@test.com"
        ).first()
        user.is_active = True
        db_session.commit()

        # Now login should work
        login_response = client.post(
            "/auth/login",
            json={
                "email": "workflow@test.com",
                "password": "TestPass123!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_token_refresh_workflow(self, client, test_user):
        """Test token refresh workflow"""
        # Login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["access_token"]

        # Use new token
        profile_response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert profile_response.status_code == status.HTTP_200_OK


class TestBusinessLogicValidation:
    """Test business rules and validation"""

    def test_price_preservation_on_order(self, client, auth_headers, sample_movie_data, db_session):
        """Test that order stores price at time of creation"""
        from app.models import Movie

        movie_id = sample_movie_data["movie"].id
        original_price = sample_movie_data["movie"].price

        # Add to cart and create order
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )
        order_response = client.post("/orders", headers=auth_headers)
        order_items = order_response.json()["items"]

        # Change movie price
        movie = db_session.query(Movie).filter(Movie.id == movie_id).first()
        movie.price = 99.99
        db_session.commit()

        # Order should still have original price
        assert float(order_items[0]["price_at_order"]) == float(original_price)

    def test_unique_email_constraint(self, client, test_user):
        """Test that duplicate emails are not allowed"""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "NewPass123!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cart_cleared_after_order(self, client, auth_headers, sample_movie_data):
        """Test that cart is cleared after creating order"""
        movie_id = sample_movie_data["movie"].id

        # Add to cart
        client.post(
            "/cart/items",
            headers=auth_headers,
            json={"movie_id": movie_id}
        )

        # Create order
        client.post("/orders", headers=auth_headers)

        # Check cart is empty
        cart_response = client.get("/cart", headers=auth_headers)
        assert cart_response.json()["items_count"] == 0


class TestRoleBasedAccess:
    """Test role-based access control"""

    def test_user_cannot_access_moderator_endpoints(self, client, auth_headers):
        """Test that users cannot access moderator endpoints"""
        response = client.get("/moderator/genres", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """Test that users cannot access admin endpoints"""
        response = client.get("/admin/users", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_moderator_cannot_access_admin_endpoints(self, client, moderator_headers):
        """Test that moderators cannot access admin-only endpoints"""
        response = client.delete(
            "/admin/users/999",
            headers=moderator_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_moderator_can_manage_movies(self, client, moderator_headers, sample_movie_data):
        """Test that moderators can manage movies"""
        response = client.get("/moderator/genres", headers=moderator_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_has_full_access(self, client, admin_headers):
        """Test that admins have access to all endpoints"""
        # Admin endpoints
        response1 = client.get("/admin/users", headers=admin_headers)
        assert response1.status_code == status.HTTP_200_OK

        # Moderator endpoints
        response2 = client.get("/moderator/genres", headers=admin_headers)
        assert response2.status_code == status.HTTP_200_OK
