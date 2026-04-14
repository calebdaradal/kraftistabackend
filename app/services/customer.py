import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.customer import CartItemIn, CheckoutRequest


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
            image_url=payload.image_url,
            product_name=payload.product_name,
        )
        db.add(item)
    else:
        existing.quantity = payload.quantity
        existing.unit_price = payload.unit_price
        existing.image_url = payload.image_url
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
