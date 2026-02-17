from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from src.database import get_db
from src.models import User, Cart, CartItem, Movie
from src.schemas.cart import (
    UserCartSummary, CartResponse, Message, MovieInCart
)
from src.dependencies import get_admin_user, get_moderator_user

router = APIRouter(prefix="/admin/carts", tags=["Admin - Cart Management"])


@router.get("", response_model=List[UserCartSummary])
def get_all_user_carts(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """
    Get summary of all user carts (Admin only)
    Useful for analytics and troubleshooting
    """
    carts = db.query(
        Cart,
        User.email,
        func.count(CartItem.id).label('items_count')
    ).join(User).outerjoin(CartItem).group_by(
        Cart.id, User.email
    ).offset(skip).limit(limit).all()

    result = []
    for cart, email, items_count in carts:
        cart_items = db.query(CartItem).options(
            joinedload(CartItem.movie)
        ).filter(CartItem.cart_id == cart.id).all()

        total_amount = sum(item.movie.price for item in cart_items if item.movie)

        result.append(UserCartSummary(
            user_id=cart.user_id,
            user_email=email,
            items_count=items_count,
            total_amount=total_amount,
            last_updated=cart.updated_at
        ))

    return result


@router.get("/{user_id}", response_model=CartResponse)
def get_user_cart(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """View a specific user's cart (Admin only)"""
    cart = db.query(Cart).options(
        joinedload(Cart.items).joinedload(CartItem.movie).joinedload(Movie.genres)
    ).filter(Cart.user_id == user_id).first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no cart"
        )

    total_amount = sum(item.movie.price for item in cart.items if item.movie)

    items_response = []
    for item in cart.items:
        if item.movie:
            movie_dict = {
                'id': item.movie.id,
                'name': item.movie.name,
                'year': item.movie.year,
                'price': item.movie.price,
                'genres': [genre.name for genre in item.movie.genres]
            }
            items_response.append({
                'id': item.id,
                'cart_id': item.cart_id,
                'movie_id': item.movie_id,
                'added_at': item.added_at,
                'movie': movie_dict
            })

    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        created_at=cart.created_at,
        updated_at=cart.updated_at,
        items=items_response,
        total_amount=total_amount,
        items_count=len(items_response)
    )


@router.get("/movie/{movie_id}/usage", response_model=Message)
def check_movie_in_carts(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_moderator_user)
):
    """
    Check if a movie exists in any user's cart (Moderator+)
    Used before deleting movies to notify moderators
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    cart_items = db.query(CartItem).filter(
        CartItem.movie_id == movie_id
    ).all()

    if not cart_items:
        return Message(
            message="Movie is not in any user's cart",
            details={
                "movie_id": movie_id,
                "movie_name": movie.name,
                "carts_count": 0
            }
        )

    user_ids = [item.cart.user_id for item in cart_items]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_emails = [user.email for user in users]

    return Message(
        message="WARNING: Movie exists in user carts",
        details={
            "movie_id": movie_id,
            "movie_name": movie.name,
            "carts_count": len(cart_items),
            "affected_users": user_emails
        }
    )


@router.delete("/user/{user_id}/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_user_cart(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Clear a specific user's cart (Admin only)"""
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no cart"
        )

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
