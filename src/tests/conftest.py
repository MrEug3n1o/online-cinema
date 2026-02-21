import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.main import app
from src.database import Base, get_db
from src.models import UserGroup, UserGroupEnum
from src.security import get_password_hash
import os


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        for group_name in UserGroupEnum:
            group = UserGroup(name=group_name)
            db.add(group)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden dependencies"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    from src.models import User, UserProfile

    # Get USER group
    user_group = db_session.query(UserGroup).filter(
        UserGroup.name == UserGroupEnum.USER
    ).first()

    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        group_id=user_group.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create profile
    profile = UserProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()

    return user


@pytest.fixture
def test_moderator(db_session):
    """Create a test moderator"""
    from src.models import User, UserProfile

    mod_group = db_session.query(UserGroup).filter(
        UserGroup.name == UserGroupEnum.MODERATOR
    ).first()

    user = User(
        email="moderator@example.com",
        hashed_password=get_password_hash("ModPass123!"),
        is_active=True,
        group_id=mod_group.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create profile
    profile = UserProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()

    return user


@pytest.fixture
def test_admin(db_session):
    """Create a test admin"""
    from src.models import User, UserProfile

    admin_group = db_session.query(UserGroup).filter(
        UserGroup.name == UserGroupEnum.ADMIN
    ).first()

    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        group_id=admin_group.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = UserProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()

    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def moderator_headers(client, test_moderator):
    """Get authentication headers for moderator"""
    response = client.post(
        "/auth/login",
        json={
            "email": "moderator@example.com",
            "password": "ModPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin"""
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_movie_data(db_session):
    """Create sample movie data"""
    from src.models import Genre, Star, Director, Certification, Movie

    cert = Certification(name="PG-13")
    db_session.add(cert)
    db_session.flush()

    genre = Genre(name="Action")
    db_session.add(genre)
    db_session.flush()

    star = Star(name="Test Actor")
    db_session.add(star)
    db_session.flush()

    director = Director(name="Test Director")
    db_session.add(director)
    db_session.flush()

    movie = Movie(
        name="Test Movie",
        year=2024,
        time=120,
        imdb=8.5,
        votes=10000,
        description="A test movie",
        price=9.99,
        certification_id=cert.id
    )
    movie.genres.append(genre)
    movie.stars.append(star)
    movie.directors.append(director)

    db_session.add(movie)
    db_session.commit()
    db_session.refresh(movie)

    return {
        "movie": movie,
        "genre": genre,
        "star": star,
        "director": director,
        "certification": cert
    }


@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    """Mock email sending"""

    def mock_send_email(*args, **kwargs):
        pass

    monkeypatch.setattr("app.email.send_email", mock_send_email)


@pytest.fixture(autouse=True)
def mock_stripe(monkeypatch):
    """Mock Stripe API calls"""

    class MockPaymentIntent:
        def __init__(self, *args, **kwargs):
            self.id = "pi_test_123"
            self.client_secret = "pi_test_123_secret"
            self.status = "succeeded"
            self.amount = 1000

    def mock_create_payment_intent(*args, **kwargs):
        return {
            'id': 'pi_test_123',
            'client_secret': 'pi_test_123_secret',
            'status': 'requires_payment_method',
            'amount': 1000
        }

    def mock_retrieve_payment_intent(*args, **kwargs):
        return {
            'id': 'pi_test_123',
            'status': 'succeeded'
        }

    monkeypatch.setattr(
        "app.services.stripe_service.StripeService.create_payment_intent",
        mock_create_payment_intent
    )
    monkeypatch.setattr(
        "app.services.stripe_service.StripeService.retrieve_payment_intent",
        mock_retrieve_payment_intent
    )
