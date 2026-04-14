import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import CartItemIn, CartRead, CheckoutRequest, OrderRead
from app.services.customer import (
    create_order_from_cart,
    get_user_cart,
    list_user_orders,
    remove_cart_item,
    upsert_cart_item,
)

router = APIRouter(prefix="/customer", tags=["customer"])


def _cart_to_read(cart) -> CartRead:
    return CartRead(
        id=cart.id,
        user_id=cart.user_id,
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "selected_variations": item.selected_variations,
                "unit_price": item.unit_price,
                "image_url": item.image_url,
                "product_name": item.product_name,
            }
            for item in cart.items
        ],
    )


@router.get("/cart", response_model=CartRead)
def get_cart_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    return _cart_to_read(get_user_cart(db, current_user))


@router.post("/cart/items", response_model=CartRead)
def add_or_update_cart_item_endpoint(
    payload: CartItemIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartRead:
    return _cart_to_read(upsert_cart_item(db, current_user, payload))


@router.delete("/cart/items/{item_id}", response_model=CartRead)
def remove_cart_item_endpoint(
    item_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartRead:
    return _cart_to_read(remove_cart_item(db, current_user, item_id))


@router.post("/checkout", response_model=OrderRead)
def checkout_endpoint(
    payload: CheckoutRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> OrderRead:
    order = create_order_from_cart(db, current_user, payload)
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        subtotal=order.subtotal,
        tax=order.tax,
        shipping=order.shipping,
        total=order.total,
        payment_method=order.payment_method,
        order_note=order.order_note,
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "selected_variations": item.selected_variations,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "product_name": item.product_name,
                "image_url": item.image_url,
            }
            for item in order.items
        ],
    )


@router.get("/orders", response_model=list[OrderRead])
def list_orders_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderRead]:
    orders = list_user_orders(db, current_user)
    return [
        OrderRead(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            subtotal=order.subtotal,
            tax=order.tax,
            shipping=order.shipping,
            total=order.total,
            payment_method=order.payment_method,
            order_note=order.order_note,
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            items=[
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "selected_variations": item.selected_variations,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                    "product_name": item.product_name,
                    "image_url": item.image_url,
                }
                for item in order.items
            ],
        )
        for order in orders
    ]
