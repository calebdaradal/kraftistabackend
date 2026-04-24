import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart, CartItem
from app.models.engagement import ProductLike, ProductReview, UserNotification
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.customer import CartItemIn, CheckoutRequest, ProductReviewCreate


def _sanitize_image_url(image_url: str | None) -> str | None:
    if not image_url:
        return None
    trimmed = image_url.strip()
    if not trimmed:
        return None
    # DB column is VARCHAR(512); drop oversized payloads (e.g. base64 data URLs) instead of 500.
    if len(trimmed) > 512:
        return None
    return trimmed


def _get_or_create_cart(db: Session, user: User) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def get_user_cart(db: Session, user: User) -> Cart:
    cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user.id))
    if cart is None:
        return _get_or_create_cart(db, user)
    return cart


def upsert_cart_item(db: Session, user: User, payload: CartItemIn) -> Cart:
    cart = _get_or_create_cart(db, user)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    existing = db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == payload.product_id,
            CartItem.selected_variations == payload.selected_variations,
        )
    )

    if existing is None:
        item = CartItem(
            cart_id=cart.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            selected_variations=payload.selected_variations,
            unit_price=payload.unit_price,
            image_url=_sanitize_image_url(payload.image_url),
            product_name=payload.product_name,
        )
        db.add(item)
    else:
        existing.quantity = payload.quantity
        existing.unit_price = payload.unit_price
        existing.image_url = _sanitize_image_url(payload.image_url)
        existing.product_name = payload.product_name

    db.commit()
    return get_user_cart(db, user)


def remove_cart_item(db: Session, user: User, item_id: uuid.UUID) -> Cart:
    cart = _get_or_create_cart(db, user)
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")
    db.delete(item)
    db.commit()
    return get_user_cart(db, user)


def clear_user_cart(db: Session, user: User) -> None:
    cart = _get_or_create_cart(db, user)
    for item in list(cart.items):
        db.delete(item)
    db.commit()


def create_order_from_cart(db: Session, user: User, payload: CheckoutRequest) -> Order:
    cart = get_user_cart(db, user)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")

    subtotal = sum(Decimal(item.unit_price) * item.quantity for item in cart.items)
    tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))
    shipping = Decimal("0.00") if subtotal >= Decimal("50.00") else Decimal("10.00")
    total = subtotal + tax + shipping

    order = Order(
        user_id=user.id,
        status="placed",
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        total=total,
        payment_method=payload.payment_method,
        order_note=payload.order_note,
        shipping_address=payload.shipping_address,
    )
    db.add(order)
    db.flush()

    for item in cart.items:
        line_total = (Decimal(item.unit_price) * item.quantity).quantize(Decimal("0.01"))
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                selected_variations=item.selected_variations,
                unit_price=item.unit_price,
                line_total=line_total,
                product_name=item.product_name,
                image_url=item.image_url,
            )
        )
        db.delete(item)

    db.commit()
    return db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))


def list_user_orders(db: Session, user: User) -> list[Order]:
    return list(
        db.scalars(
            select(Order).options(selectinload(Order.items)).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        ).all()
    )


def get_user_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.user_id == user.id, Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


def list_user_likes(db: Session, user: User) -> list[ProductLike]:
    return list(db.scalars(select(ProductLike).where(ProductLike.user_id == user.id).order_by(ProductLike.created_at.desc())).all())


def add_user_like(db: Session, user: User, product_id: uuid.UUID) -> ProductLike:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    existing = db.scalar(select(ProductLike).where(ProductLike.user_id == user.id, ProductLike.product_id == product_id))
    if existing is not None:
        return existing

    like = ProductLike(user_id=user.id, product_id=product_id)
    db.add(like)
    db.commit()
    db.refresh(like)
    return like


def remove_user_like(db: Session, user: User, product_id: uuid.UUID) -> None:
    existing = db.scalar(select(ProductLike).where(ProductLike.user_id == user.id, ProductLike.product_id == product_id))
    if existing is None:
        return
    db.delete(existing)
    db.commit()


def list_pending_review_items(db: Session, user: User, max_days: int = 7) -> list[tuple[Order, OrderItem]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    rows = db.execute(
        select(Order, OrderItem)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .outerjoin(ProductReview, ProductReview.order_item_id == OrderItem.id)
        .where(
            Order.user_id == user.id,
            Order.status == "delivered",
            ProductReview.id.is_(None),
            # Hide items whose review window has already expired
            or_(Order.delivered_at.is_(None), Order.delivered_at >= cutoff),
        )
        .order_by(Order.created_at.desc(), OrderItem.id.asc())
    ).all()
    return list(rows)


def create_review_for_order_item(
    db: Session, user: User, payload: ProductReviewCreate, min_days: int = 3, max_days: int = 7
) -> ProductReview:
    existing = db.scalar(select(ProductReview).where(ProductReview.order_item_id == payload.order_item_id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already submitted for this order item.")

    row = db.execute(
        select(Order, OrderItem)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(OrderItem.id == payload.order_item_id, Order.user_id == user.id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found.")

    order, order_item = row
    if order.status != "delivered":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can only review delivered items.")

    if order.delivered_at is not None:
        now = datetime.now(timezone.utc)
        days_since = (now - order.delivered_at).days
        if days_since < min_days:
            available_in = min_days - days_since
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reviews can be submitted {min_days} days after delivery. Available in {available_in} day(s).",
            )
        if days_since > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Review window has expired. Reviews must be submitted within {max_days} days of delivery.",
            )

    review = ProductReview(
        user_id=user.id,
        product_id=order_item.product_id,
        order_id=order.id,
        order_item_id=order_item.id,
        rating=payload.rating,
        comment=payload.comment,
        moderation_status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_user_reviews(db: Session, user: User) -> list[ProductReview]:
    return list(
        db.scalars(select(ProductReview).where(ProductReview.user_id == user.id).order_by(ProductReview.created_at.desc())).all()
    )


def get_pending_review_count(db: Session, user: User) -> int:
    count = db.scalar(
        select(func.count(OrderItem.id))
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .outerjoin(ProductReview, ProductReview.order_item_id == OrderItem.id)
        .where(Order.user_id == user.id, Order.status == "delivered", ProductReview.id.is_(None))
    )
    return int(count or 0)


def sync_pending_review_notification(db: Session, user: User) -> None:
    pending_count = get_pending_review_count(db, user)
    existing = db.scalar(
        select(UserNotification).where(UserNotification.user_id == user.id, UserNotification.kind == "pending_reviews")
    )
    if pending_count <= 0:
        if existing is not None:
            db.delete(existing)
            db.commit()
        return

    message = f"You have {pending_count} product review(s) pending."
    if existing is None:
        db.add(UserNotification(user_id=user.id, kind="pending_reviews", message=message, is_read=False))
    else:
        existing.message = message
        existing.is_read = False
    db.commit()
