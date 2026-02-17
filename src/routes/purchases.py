from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List
from decimal import Decimal
import uuid
from datetime import datetime
from src.database import get_db
from src.models import User, Cart, CartItem, Movie, Purchase, PurchaseItem
from src.schemas.cart import (
    CheckoutRequest, PurchaseResponse, PurchaseListItem,
    PaginatedPurchases, PurchasedMovieResponse, Message, MovieInCart
)
from src.dependencies import get_current_active_user

router = APIRouter(prefix="/purchases", tags=["Purchases"])


def _build_movie_in_cart(movie: Movie) -> dict:
    """Build movie dict for response"""
    return {
        'id': movie.id,
        'name': movie.name,
        'year': movie.year,
        'price': movie.price,
        'genres': [genre.name for genre in movie.genres]
    }


@router.post("/checkout", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
def checkout(
        checkout_data: CheckoutRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Process checkout: create purchase from cart items
    Validates all movies are available and not already purchased
    """
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )

    cart_items = db.query(CartItem).options(
        joinedload(CartItem.movie).joinedload(Movie.genres)
    ).filter(CartItem.cart_id == cart.id).all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )

    already_purchased = []
    unavailable_movies = []
    valid_items = []

    for item in cart_items:
        if not item.movie:
            unavailable_movies.append(item.movie_id)
            continue

        existing_purchase = db.query(PurchaseItem).filter(
            PurchaseItem.user_id == current_user.id,
            PurchaseItem.movie_id == item.movie_id
        ).first()

        if existing_purchase:
            already_purchased.append({
                'id': item.movie.id,
                'name': item.movie.name
            })
            continue

        valid_items.append(item)

    if already_purchased or unavailable_movies:
        error_details = {}
        if already_purchased:
            error_details['already_purchased'] = already_purchased
        if unavailable_movies:
            error_details['unavailable'] = unavailable_movies

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some movies cannot be purchased",
            headers={"X-Error-Details": str(error_details)}
        )

    if not valid_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid items to purchase"
        )

    total_amount = sum(item.movie.price for item in valid_items)

    transaction_id = str(uuid.uuid4())
    purchase = Purchase(
        user_id=current_user.id,
        total_amount=total_amount,
        payment_method=checkout_data.payment_method,
        payment_status="completed",
        transaction_id=transaction_id
    )
    db.add(purchase)
    db.flush()

    for item in valid_items:
        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            movie_id=item.movie_id,
            user_id=current_user.id,
            price_at_purchase=item.movie.price
        )
        db.add(purchase_item)

    for item in cart_items:
        db.delete(item)

    db.commit()
    db.refresh(purchase)

    purchase = db.query(Purchase).options(
        joinedload(Purchase.items).joinedload(PurchaseItem.movie).joinedload(Movie.genres)
    ).filter(Purchase.id == purchase.id).first()

    items_response = []
    for item in purchase.items:
        movie_dict = _build_movie_in_cart(item.movie)
        items_response.append({
            'id': item.id,
            'movie_id': item.movie_id,
            'price_at_purchase': item.price_at_purchase,
            'movie': movie_dict
        })

    return PurchaseResponse(
        id=purchase.id,
        user_id=purchase.user_id,
        total_amount=purchase.total_amount,
        payment_method=purchase.payment_method,
        payment_status=purchase.payment_status,
        transaction_id=purchase.transaction_id,
        created_at=purchase.created_at,
        items=items_response
    )


@router.get("", response_model=PaginatedPurchases)
def get_purchases(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's purchase history"""
    query = db.query(Purchase).filter(
        Purchase.user_id == current_user.id
    ).order_by(desc(Purchase.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    purchases = query.offset(offset).limit(page_size).all()

    purchase_list = []
    for purchase in purchases:
        items_count = db.query(PurchaseItem).filter(
            PurchaseItem.purchase_id == purchase.id
        ).count()

        purchase_list.append(PurchaseListItem(
            id=purchase.id,
            total_amount=purchase.total_amount,
            payment_method=purchase.payment_method,
            payment_status=purchase.payment_status,
            created_at=purchase.created_at,
            items_count=items_count
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedPurchases(
        items=purchase_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase_detail(
        purchase_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get detailed information about a specific purchase"""
    purchase = db.query(Purchase).options(
        joinedload(Purchase.items).joinedload(PurchaseItem.movie).joinedload(Movie.genres)
    ).filter(
        Purchase.id == purchase_id,
        Purchase.user_id == current_user.id
    ).first()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )

    items_response = []
    for item in purchase.items:
        movie_dict = _build_movie_in_cart(item.movie)
        items_response.append({
            'id': item.id,
            'movie_id': item.movie_id,
            'price_at_purchase': item.price_at_purchase,
            'movie': movie_dict
        })

    return PurchaseResponse(
        id=purchase.id,
        user_id=purchase.user_id,
        total_amount=purchase.total_amount,
        payment_method=purchase.payment_method,
        payment_status=purchase.payment_status,
        transaction_id=purchase.transaction_id,
        created_at=purchase.created_at,
        items=items_response
    )


@router.get("/movies/list", response_model=List[PurchasedMovieResponse])
def get_purchased_movies(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get list of all purchased movies"""
    purchased_items = db.query(PurchaseItem).options(
        joinedload(PurchaseItem.movie).joinedload(Movie.genres),
        joinedload(PurchaseItem.purchase)
    ).filter(
        PurchaseItem.user_id == current_user.id
    ).order_by(desc(PurchaseItem.purchase.has(Purchase.created_at))).all()

    result = []
    for item in purchased_items:
        movie_dict = _build_movie_in_cart(item.movie)
        result.append(PurchasedMovieResponse(
            movie=movie_dict,
            purchased_at=item.purchase.created_at,
            price_paid=item.price_at_purchase
        ))

    return result


@router.get("/check/{movie_id}", response_model=Message)
def check_movie_purchased(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Check if a specific movie has been purchased"""
    purchase_item = db.query(PurchaseItem).filter(
        PurchaseItem.user_id == current_user.id,
        PurchaseItem.movie_id == movie_id
    ).first()

    if purchase_item:
        return Message(
            message="purchased",
            details={
                "movie_id": movie_id,
                "purchased_at": purchase_item.purchase.created_at.isoformat(),
                "price_paid": str(purchase_item.price_at_purchase)
            }
        )

    return Message(
        message="not_purchased",
        details={"movie_id": movie_id}
    )
