from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from decimal import Decimal
from src.database import get_db
from src.models import User, Cart, CartItem, Movie, PurchaseItem, Genre
from src.schemas.cart import (
    CartItemAdd, CartItemResponse, CartResponse, CartSummary,
    Message, MovieInCart
)
from src.dependencies import get_current_active_user

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


def _get_or_create_cart(user_id: int, db: Session) -> Cart:
    """Get user's cart or create one if it doesn't exist"""
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _check_movie_purchased(user_id: int, movie_id: int, db: Session) -> bool:
    """Check if user has already purchased the movie"""
    purchase = db.query(PurchaseItem).filter(
        PurchaseItem.user_id == user_id,
        PurchaseItem.movie_id == movie_id
    ).first()
    return purchase is not None


def _build_movie_in_cart(movie: Movie) -> dict:
    """Build movie dict for cart response"""
    return {
        'id': movie.id,
        'name': movie.name,
        'year': movie.year,
        'price': movie.price,
        'genres': [genre.name for genre in movie.genres]
    }


@router.get("", response_model=CartResponse)
def get_cart(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's shopping cart with all items"""
    cart = _get_or_create_cart(current_user.id, db)

    cart = db.query(Cart).options(
        joinedload(Cart.items).joinedload(CartItem.movie).joinedload(Movie.genres)
    ).filter(Cart.id == cart.id).first()

    total_amount = sum(item.movie.price for item in cart.items)

    items_response = []
    for item in cart.items:
        movie_dict = _build_movie_in_cart(item.movie)
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
        items_count=len(cart.items)
    )


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
        item_data: CartItemAdd,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Add a movie to the shopping cart"""
    movie = db.query(Movie).options(
        joinedload(Movie.genres)
    ).filter(Movie.id == item_data.movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    if _check_movie_purchased(current_user.id, item_data.movie_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already purchased this movie. Repeat purchases are not allowed."
        )

    cart = _get_or_create_cart(current_user.id, db)

    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == item_data.movie_id
    ).first()

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie is already in your cart"
        )

    cart_item = CartItem(
        cart_id=cart.id,
        movie_id=item_data.movie_id
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    cart_item = db.query(CartItem).options(
        joinedload(CartItem.movie).joinedload(Movie.genres)
    ).filter(CartItem.id == cart_item.id).first()

    movie_dict = _build_movie_in_cart(cart_item.movie)

    return CartItemResponse(
        id=cart_item.id,
        cart_id=cart_item.cart_id,
        movie_id=cart_item.movie_id,
        added_at=cart_item.added_at,
        movie=movie_dict
    )


@router.delete("/items/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove a movie from the shopping cart"""
    cart = _get_or_create_cart(current_user.id, db)

    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == movie_id
    ).first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found in cart"
        )

    db.delete(cart_item)
    db.commit()


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Clear all items from the shopping cart"""
    cart = _get_or_create_cart(current_user.id, db)

    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()


@router.get("/summary", response_model=CartSummary)
def get_cart_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get a quick summary of the cart (items count and total)"""
    cart = _get_or_create_cart(current_user.id, db)

    items = db.query(CartItem).options(
        joinedload(CartItem.movie).joinedload(Movie.genres)
    ).filter(CartItem.cart_id == cart.id).all()

    total_amount = sum(item.movie.price for item in items)

    movies = [_build_movie_in_cart(item.movie) for item in items]

    return CartSummary(
        items_count=len(items),
        total_amount=total_amount,
        movies=movies
    )


@router.post("/validate", response_model=Message)
def validate_cart(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Validate cart before checkout
    Checks for already purchased movies and removes them
    """
    cart = _get_or_create_cart(current_user.id, db)

    items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )

    removed_movies = []
    unavailable_movies = []

    for item in items:
        if _check_movie_purchased(current_user.id, item.movie_id, db):
            removed_movies.append(item.movie_id)
            db.delete(item)
            continue

        movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
        if not movie:
            unavailable_movies.append(item.movie_id)
            db.delete(item)

    db.commit()

    details = {}
    if removed_movies:
        details['already_purchased'] = removed_movies
    if unavailable_movies:
        details['unavailable'] = unavailable_movies

    if removed_movies or unavailable_movies:
        return Message(
            message="Some items were removed from your cart",
            details=details
        )

    return Message(
        message="Cart is valid and ready for checkout"
    )


@router.get("/check-movie/{movie_id}", response_model=Message)
def check_movie_status(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Check if a movie can be added to cart
    Returns status: can_add, already_purchased, already_in_cart, not_found
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return Message(
            message="not_found",
            details={"movie_id": movie_id}
        )

    if _check_movie_purchased(current_user.id, movie_id, db):
        return Message(
            message="already_purchased",
            details={
                "movie_id": movie_id,
                "movie_name": movie.name
            }
        )

    cart = _get_or_create_cart(current_user.id, db)
    in_cart = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == movie_id
    ).first()

    if in_cart:
        return Message(
            message="already_in_cart",
            details={
                "movie_id": movie_id,
                "movie_name": movie.name
            }
        )

    return Message(
        message="can_add",
        details={
            "movie_id": movie_id,
            "movie_name": movie.name,
            "price": str(movie.price)
        }
    )
