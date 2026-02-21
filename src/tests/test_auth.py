import pytest
from fastapi import status


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewPass123!"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email"""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "StrongPass123!"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login endpoint"""

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user"""
        from src.models import User, UserGroup, UserGroupEnum

        user_group = db_session.query(UserGroup).filter(
            UserGroup.name == UserGroupEnum.USER
        ).first()

        user = User(
            email="inactive@example.com",
            hashed_password="hashed",
            is_active=False,
            group_id=user_group.id
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test token refresh endpoint"""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # Login to get refresh token
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordChange:
    """Test password change endpoint"""

    def test_change_password_success(self, client, auth_headers):
        """Test successful password change"""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "TestPass123!",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify new password works
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "NewPass456!"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old(self, client, auth_headers):
        """Test password change with wrong old password"""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "WrongPass123!",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthorized(self, client):
        """Test password change without authentication"""
        response = client.post(
            "/auth/change-password",
            json={
                "old_password": "TestPass123!",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Test logout endpoint"""

    def test_logout_success(self, client, test_user):
        """Test successful logout"""
        # Login first
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!"
            }
        )
        tokens = login_response.json()

        # Logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify refresh token is invalidated
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordValidation:
    """Test password validation logic"""

    @pytest.mark.parametrize("password,should_pass", [
        ("Pass123!", True),
        ("ValidPassword1!", True),
        ("short1!", False),  # Too short
        ("nouppercase1!", False),  # No uppercase
        ("NOLOWERCASE1!", False),  # No lowercase
        ("NoDigits!", False),  # No digits
        ("NoSpecial123", False),  # No special char
        ("P@ss1", False),  # Too short
    ])
    def test_password_validation(self, client, password, should_pass):
        """Test password validation rules"""
        response = client.post(
            "/auth/register",
            json={
                "email": f"test_{password}@example.com",
                "password": password
            }
        )
        if should_pass:
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST  # Duplicate email
            ]
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
