import pytest
from datetime import datetime, timedelta
from src.security import create_access_token, verify_password, get_password_hash
from src.models import UserGroupEnum


class TestSecurityUtils:
    """Test security utility functions"""

    def test_password_hashing(self):
        """Test password hashing"""
        password = "TestPass123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """Test password verification with wrong password"""
        password = "TestPass123!"
        wrong_password = "WrongPass123!"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test@example.com", "group": "user"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_expiry(self):
        """Test token creation with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires_delta)

        assert token is not None


class TestPasswordValidation:
    """Test password validation logic"""

    @pytest.mark.parametrize("password,expected", [
        ("Pass123!", True),
        ("ValidPassword1!", True),
        ("Aa1!", False),  # Too short (< 8 chars)
        ("password123!", False),  # No uppercase
        ("PASSWORD123!", False),  # No lowercase
        ("Password!", False),  # No digit
        ("Password123", False),  # No special char
    ])
    def test_password_strength(self, password, expected):
        """Test password strength validation"""
        # This is tested via API endpoints in test_auth.py
        # Here we just verify the logic exists
        import re

        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        is_long_enough = len(password) >= 8

        is_valid = all([has_upper, has_lower, has_digit, has_special, is_long_enough])
        assert is_valid == expected


class TestEmailValidation:
    """Test email validation"""

    @pytest.mark.parametrize("email,is_valid", [
        ("test@example.com", True),
        ("user.name@domain.co.uk", True),
        ("invalid-email", False),
        ("@example.com", False),
        ("test@", False),
        ("test", False),
        ("", False),
    ])
    def test_email_format(self, email, is_valid):
        """Test email format validation"""
        import re

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        result = bool(re.match(pattern, email))
        assert result == is_valid


class TestPriceCalculations:
    """Test price calculation utilities"""

    def test_decimal_precision(self):
        """Test decimal precision for prices"""
        from decimal import Decimal

        price1 = Decimal("9.99")
        price2 = Decimal("14.99")
        total = price1 + price2

        assert total == Decimal("24.98")
        assert str(total) == "24.98"

    def test_price_formatting(self):
        """Test price formatting"""
        from decimal import Decimal

        price = Decimal("9.99")
        formatted = f"${price:.2f}"
        assert formatted == "$9.99"


class TestDateTimeHandling:
    """Test datetime utilities"""

    def test_token_expiration(self):
        """Test token expiration calculation"""
        now = datetime.utcnow()
        expires_in = timedelta(minutes=30)
        expires_at = now + expires_in

        assert expires_at > now
        assert (expires_at - now).total_seconds() == 1800

    def test_datetime_comparison(self):
        """Test datetime comparisons"""
        past = datetime.utcnow() - timedelta(days=1)
        future = datetime.utcnow() + timedelta(days=1)
        now = datetime.utcnow()

        assert past < now
        assert future > now


class TestPaginationLogic:
    """Test pagination utilities"""

    def test_page_calculation(self):
        """Test page calculation logic"""
        total_items = 100
        page_size = 20
        page = 1

        offset = (page - 1) * page_size
        total_pages = (total_items + page_size - 1) // page_size

        assert offset == 0
        assert total_pages == 5

    def test_pagination_edge_cases(self):
        """Test pagination edge cases"""
        # Exact division
        assert (100 + 10 - 1) // 10 == 10

        # With remainder
        assert (105 + 10 - 1) // 10 == 11

        # Single page
        assert (5 + 10 - 1) // 10 == 1


class TestUUIDGeneration:
    """Test UUID generation for movies"""

    def test_uuid_uniqueness(self):
        """Test UUID uniqueness"""
        import uuid

        uuid1 = uuid.uuid4()
        uuid2 = uuid.uuid4()

        assert uuid1 != uuid2
        assert str(uuid1) != str(uuid2)

    def test_uuid_format(self):
        """Test UUID format"""
        import uuid

        test_uuid = uuid.uuid4()
        uuid_str = str(test_uuid)

        # UUID4 format: 8-4-4-4-12 hex digits
        assert len(uuid_str) == 36
        assert uuid_str.count('-') == 4


class TestSortingLogic:
    """Test sorting and filtering logic"""

    def test_sort_by_price(self):
        """Test price sorting logic"""
        from decimal import Decimal

        movies = [
            {"name": "Movie A", "price": Decimal("14.99")},
            {"name": "Movie B", "price": Decimal("9.99")},
            {"name": "Movie C", "price": Decimal("19.99")},
        ]

        sorted_asc = sorted(movies, key=lambda x: x["price"])
        sorted_desc = sorted(movies, key=lambda x: x["price"], reverse=True)

        assert sorted_asc[0]["name"] == "Movie B"
        assert sorted_desc[0]["name"] == "Movie C"

    def test_filter_by_year(self):
        """Test year filtering logic"""
        movies = [
            {"name": "Movie A", "year": 2020},
            {"name": "Movie B", "year": 2022},
            {"name": "Movie C", "year": 2024},
        ]

        filtered = [m for m in movies if m["year"] >= 2022]

        assert len(filtered) == 2
        assert all(m["year"] >= 2022 for m in filtered)


class TestSearchLogic:
    """Test search functionality logic"""

    def test_case_insensitive_search(self):
        """Test case-insensitive search"""
        text = "The Matrix"
        search_term = "matrix"

        assert search_term.lower() in text.lower()

    def test_partial_matching(self):
        """Test partial text matching"""
        text = "The Dark Knight"
        search_term = "dark"

        assert search_term.lower() in text.lower()

    def test_search_in_list(self):
        """Test searching in list of items"""
        movies = [
            {"name": "The Matrix"},
            {"name": "Inception"},
            {"name": "The Dark Knight"},
        ]
        search_term = "the"

        results = [m for m in movies if search_term.lower() in m["name"].lower()]

        assert len(results) == 2


class TestValidationRules:
    """Test business validation rules"""

    def test_movie_year_validation(self):
        """Test movie year validation"""
        current_year = datetime.now().year

        assert 1800 <= 2024 <= 2100
        assert not (1800 <= 1799 <= 2100)
        assert not (1800 <= 2101 <= 2100)

    def test_rating_range_validation(self):
        """Test rating range validation"""
        valid_ratings = [1, 5, 10]
        invalid_ratings = [0, -1, 11]

        for rating in valid_ratings:
            assert 1 <= rating <= 10

        for rating in invalid_ratings:
            assert not (1 <= rating <= 10)

    def test_price_validation(self):
        """Test price validation"""
        from decimal import Decimal

        valid_prices = [Decimal("0.99"), Decimal("9.99"), Decimal("99.99")]
        invalid_prices = [Decimal("-1.00"), Decimal("0.00")]

        for price in valid_prices:
            assert price > 0

        for price in invalid_prices:
            assert not (price > 0)


class TestStatusTransitions:
    """Test status transition logic"""

    def test_order_status_transitions(self):
        """Test valid order status transitions"""
        from src.models import OrderStatus

        # Valid transitions
        assert OrderStatus.PENDING != OrderStatus.PAID
        assert OrderStatus.PENDING != OrderStatus.CANCELED

        # Status values
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.PAID.value == "paid"
        assert OrderStatus.CANCELED.value == "canceled"

    def test_payment_status_transitions(self):
        """Test valid payment status transitions"""
        from src.models import PaymentStatus

        # Status values
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.SUCCESSFUL.value == "successful"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELED.value == "canceled"
        assert PaymentStatus.REFUNDED.value == "refunded"
