from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
from typing import Optional
from decimal import Decimal
import uuid
from datetime import datetime
from src.database import get_db
from src.models import (
    User, Order, OrderItem, OrderStatus,
    Cart, CartItem, Movie, PurchaseItem, Purchase
)
from src.schemas.order import (
    OrderCreate, OrderResponse, OrderListItem, PaginatedOrders,
    PaymentRequest, PaymentResponse, OrderCancelRequest,
    OrderValidationResult, Message, OrderItemResponse
)
from src.dependencies import get_current_active_user
from src.email import send_email

router = APIRouter(prefix="/orders", tags=["Orders"])


def _build_movie_dict(movie: Movie) -> dict:
    """Build movie dictionary for response"""
    return {
        'id': movie.id,
        'name': movie.name,
        'year': movie.year,
        'price': movie.price,
        'genres': [genre.name for genre in movie.genres]
    }


def _check_movie_already_purchased(user_id: int, movie_id: int, db: Session) -> bool:
    """Check if user already purchased this movie"""
    return db.query(PurchaseItem).filter(
        PurchaseItem.user_id == user_id,
        PurchaseItem.movie_id == movie_id
    ).first() is not None


def _check_pending_order_with_movie(user_id: int, movie_id: int, db: Session) -> Optional[int]:
    """Check if movie is in any pending order"""
    pending_order = db.query(Order).join(OrderItem).filter(
        Order.user_id == user_id,
        Order.status == OrderStatus.PENDING,
        OrderItem.movie_id == movie_id
    ).first()
    return pending_order.id if pending_order else None


def send_order_confirmation_email(user_email: str, order_id: int, total_amount: Decimal):
    """Send order confirmation email"""
    subject = f"Order #{order_id} Confirmed - Online Cinema"
    body = f"""
    <html>
        <body>
            <h2>Order Confirmation</h2>
            <p>Thank you for your purchase!</p>
            <p><strong>Order ID:</strong> {order_id}</p>
            <p><strong>Total Amount:</strong> ${total_amount}</p>
            <p>Your movies are now available in your library.</p>
            <br>
            <p>Best regards,<br>Online Cinema Team</p>
        </body>
    </html>
    """
    send_email(user_email, subject, body)


@router.post("/validate", response_model=OrderValidationResult)
def validate_order(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Validate cart before creating order
    - Checks cart not empty
    - Excludes already purchased movies
    - Excludes unavailable movies
    - Checks for pending orders with same movies
    - Calculates total amount
    """
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        return OrderValidationResult(
            valid=False,
            message="Cart is empty"
        )

    cart_items = db.query(CartItem).options(
        joinedload(CartItem.movie)
    ).filter(CartItem.cart_id == cart.id).all()

    if not cart_items:
        return OrderValidationResult(
            valid=False,
            message="Cart is empty"
        )

    excluded_movies = []
    valid_items = []
    pending_orders = []

    for item in cart_items:
        if not item.movie:
            excluded_movies.append({
                'movie_id': item.movie_id,
                'reason': 'Movie not found or unavailable'
            })
            continue

        if _check_movie_already_purchased(current_user.id, item.movie_id, db):
            excluded_movies.append({
                'movie_id': item.movie_id,
                'name': item.movie.name,
                'reason': 'Already purchased'
            })
            continue

        pending_order_id = _check_pending_order_with_movie(current_user.id, item.movie_id, db)
        if pending_order_id:
            excluded_movies.append({
                'movie_id': item.movie_id,
                'name': item.movie.name,
                'reason': f'Already in pending order #{pending_order_id}'
            })
            if pending_order_id not in pending_orders:
                pending_orders.append(pending_order_id)
            continue

        valid_items.append(item)

    if not valid_items:
        return OrderValidationResult(
            valid=False,
            message="No valid items to order",
            excluded_movies=excluded_movies,
            pending_orders=pending_orders
        )

    total_amount = sum(item.movie.price for item in valid_items)

    if excluded_movies:
        return OrderValidationResult(
            valid=True,
            message=f"{len(valid_items)} items valid, {len(excluded_movies)} excluded",
            excluded_movies=excluded_movies,
            total_amount=total_amount,
            pending_orders=pending_orders
        )

    return OrderValidationResult(
        valid=True,
        message="All items valid",
        total_amount=total_amount
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
        order_data: OrderCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Create order from cart
    - Validates all items
    - Excludes already purchased/unavailable movies
    - Creates order with PENDING status
    - Removes items from cart
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

    valid_items = []
    excluded_movies = []

    for item in cart_items:
        if not item.movie:
            excluded_movies.append({
                'movie_id': item.movie_id,
                'reason': 'unavailable'
            })
            continue

        if _check_movie_already_purchased(current_user.id, item.movie_id, db):
            excluded_movies.append({
                'movie_id': item.movie_id,
                'name': item.movie.name,
                'reason': 'already_purchased'
            })
            continue

        pending_order_id = _check_pending_order_with_movie(current_user.id, item.movie_id, db)
        if pending_order_id:
            excluded_movies.append({
                'movie_id': item.movie_id,
                'name': item.movie.name,
                'reason': 'in_pending_order',
                'order_id': pending_order_id
            })
            continue

        valid_items.append(item)

    if not valid_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid items to order",
            headers={"X-Excluded-Movies": str(excluded_movies)}
        )

    total_amount = sum(item.movie.price for item in valid_items)

    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING,
        total_amount=total_amount
    )
    db.add(order)
    db.flush()

    for item in valid_items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=item.movie_id,
            price_at_order=item.movie.price
        )
        db.add(order_item)

    for item in valid_items:
        db.delete(item)

    db.commit()
    db.refresh(order)

    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.movie).joinedload(Movie.genres)
    ).filter(Order.id == order.id).first()

    items_response = []
    for item in order.items:
        movie_dict = _build_movie_dict(item.movie)
        items_response.append({
            'id': item.id,
            'order_id': item.order_id,
            'movie_id': item.movie_id,
            'price_at_order': item.price_at_order,
            'movie': movie_dict
        })

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        status=order.status,
        total_amount=order.total_amount,
        payment_gateway_reference=order.payment_gateway_reference,
        items=items_response,
        items_count=len(items_response)
    )


@router.get("", response_model=PaginatedOrders)
def get_orders(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        status: Optional[OrderStatus] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's orders with pagination and optional status filter"""
    query = db.query(Order).filter(Order.user_id == current_user.id)

    if status:
        query = query.filter(Order.status == status)

    query = query.order_by(desc(Order.created_at))

    total = query.count()

    offset = (page - 1) * page_size
    orders = query.offset(offset).limit(page_size).all()

    order_list = []
    for order in orders:
        items_count = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).count()

        order_list.append(OrderListItem(
            id=order.id,
            created_at=order.created_at,
            status=order.status,
            total_amount=order.total_amount,
            items_count=items_count
        ))

    total_pages = (total + page_size - 1) // page_size

    return PaginatedOrders(
        items=order_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get detailed order information"""
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.movie).joinedload(Movie.genres)
    ).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    items_response = []
    for item in order.items:
        movie_dict = _build_movie_dict(item.movie)
        items_response.append({
            'id': item.id,
            'order_id': item.order_id,
            'movie_id': item.movie_id,
            'price_at_order': item.price_at_order,
            'movie': movie_dict
        })

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        status=order.status,
        total_amount=order.total_amount,
        payment_gateway_reference=order.payment_gateway_reference,
        items=items_response,
        items_count=len(items_response)
    )


@router.post("/{order_id}/pay", response_model=PaymentResponse)
def process_payment(
        order_id: int,
        payment_data: PaymentRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Process payment for order
    - Revalidates total amount
    - Processes payment (mock)
    - Updates order status to PAID
    - Creates purchase record
    - Sends confirmation email
    """
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.movie)
    ).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order status is {order.status.value}, cannot process payment"
        )

    current_total = sum(item.price_at_order for item in order.items)
    if current_total != order.total_amount:
        order.total_amount = current_total

    payment_reference = f"PAY-{uuid.uuid4()}"

    order.status = OrderStatus.PAID
    order.payment_gateway_reference = payment_reference

    purchase = Purchase(
        user_id=current_user.id,
        total_amount=order.total_amount,
        payment_method=payment_data.payment_method,
        payment_status="completed",
        transaction_id=payment_reference
    )
    db.add(purchase)
    db.flush()

    for order_item in order.items:
        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            movie_id=order_item.movie_id,
            user_id=current_user.id,
            price_at_purchase=order_item.price_at_order
        )
        db.add(purchase_item)

    db.commit()

    background_tasks.add_task(
        send_order_confirmation_email,
        current_user.email,
        order.id,
        order.total_amount
    )

    return PaymentResponse(
        order_id=order.id,
        payment_gateway_reference=payment_reference,
        redirect_url=None,
        status="success",
        message="Payment processed successfully. Confirmation email sent."
    )


@router.post("/{order_id}/cancel", response_model=Message)
def cancel_order(
        order_id: int,
        cancel_data: OrderCancelRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Cancel order
    - Only PENDING orders can be cancelled directly
    - PAID orders require refund request
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already canceled"
        )

    if order.status == OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid orders cannot be cancelled directly. Please submit a refund request."
        )

    order.status = OrderStatus.CANCELED
    db.commit()

    return Message(
        message="Order cancelled successfully",
        details={
            "order_id": order.id,
            "reason": cancel_data.reason
        }
    )
