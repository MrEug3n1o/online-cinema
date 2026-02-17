from sqlalchemy import Column, Integer, ForeignKey, DateTime, DECIMAL, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('carts.id', ondelete='CASCADE'), nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id', ondelete='CASCADE'), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('cart_id', 'movie_id', name='uix_cart_movie'),
    )

    cart = relationship("Cart", back_populates="items")
    movie = relationship("Movie")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(String, nullable=False)  # e.g., "credit_card", "paypal"
    payment_status = Column(String, nullable=False, default="completed")  # completed, pending, failed
    transaction_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    user = relationship("User", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id', ondelete='CASCADE'), nullable=False)
    movie_id = Column(Integer, ForeignKey('movies.id', ondelete='RESTRICT'), nullable=False)
    price_at_purchase = Column(DECIMAL(10, 2), nullable=False)  # Store price at time of purchase

    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='uix_user_movie_purchase'),
    )

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    movie = relationship("Movie")
    user = relationship("User", back_populates="purchased_movies")