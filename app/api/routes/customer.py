import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.engagement import ProductReview
from app.models.settings import SiteSetting
from app.models.user import User
from app.schemas.customer import (
    CartItemIn,
    CartRead,
    CheckoutRequest,
    OrderRead,
    PendingReviewItemRead,
    ProductLikeCreate,
    ProductLikeRead,
    ProductReviewCreate,
    ProductReviewRead,
    ReviewNotificationRead,
)
from app.schemas.orders import RefundRequestPayload
from app.services.customer import (
    add_user_like,
    create_review_for_order_item,
    create_order_from_cart,
    get_pending_review_count,
    get_user_order,
    get_user_cart,
    list_pending_review_items,
    list_user_likes,
    list_user_orders,
    list_user_reviews,
    remove_cart_item,
    remove_user_like,
    sync_pending_review_notification,
    upsert_cart_item,
)

router = APIRouter(prefix="/customer", tags=["customer"])

_SETTINGS_KEY = "site"


def _get_review_window(db: Session) -> tuple[int, int]:
    """Return (min_days, max_days) from site settings with defaults 3 / 7."""
    row = db.query(SiteSetting).filter(SiteSetting.key == _SETTINGS_KEY).one_or_none()
    data = row.data if row and isinstance(row.data, dict) else {}
    min_days = max(0, int(data.get("reviewMinDays") or 3))
    max_days = max(1, int(data.get("reviewMaxDays") or 7))
    return min_days, max_days


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


def _order_to_read(order) -> OrderRead:
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
        tracking_reference=order.tracking_reference,
        delivered_at=order.delivered_at,
        created_at=order.created_at,
        refund_requested=bool(getattr(order, "refund_requested", False)),
        refund_note=getattr(order, "refund_note", None),
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


def _review_to_read(review: ProductReview, product_name: str, image_url: str | None) -> ProductReviewRead:
    return ProductReviewRead(
        id=review.id,
        order_id=review.order_id,
        order_item_id=review.order_item_id,
        product_id=review.product_id,
        product_name=product_name,
        image_url=image_url,
        rating=review.rating,
        comment=review.comment,
        moderation_status=review.moderation_status,
        moderation_note=review.moderation_note,
        created_at=review.created_at,
        updated_at=review.updated_at,
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
    return _order_to_read(order)


@router.get("/orders", response_model=list[OrderRead])
def list_orders_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderRead]:
    orders = list_user_orders(db, current_user)
    return [_order_to_read(order) for order in orders]


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order_endpoint(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderRead:
    return _order_to_read(get_user_order(db, current_user, order_id))


@router.get("/likes", response_model=list[ProductLikeRead])
def list_likes_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProductLikeRead]:
    likes = list_user_likes(db, current_user)
    return [ProductLikeRead(id=like.id, product_id=like.product_id, created_at=like.created_at) for like in likes]


@router.post("/likes", response_model=ProductLikeRead, status_code=201)
def create_like_endpoint(
    payload: ProductLikeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProductLikeRead:
    like = add_user_like(db, current_user, payload.product_id)
    return ProductLikeRead(id=like.id, product_id=like.product_id, created_at=like.created_at)


@router.delete("/likes/{product_id}", status_code=204)
def delete_like_endpoint(product_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    remove_user_like(db, current_user, product_id)


@router.get("/reviews/pending", response_model=list[PendingReviewItemRead])
def list_pending_reviews_endpoint(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[PendingReviewItemRead]:
    _min_days, max_days = _get_review_window(db)
    rows = list_pending_review_items(db, current_user, max_days=max_days)
    return [
        PendingReviewItemRead(
            order_id=order.id,
            order_item_id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            image_url=item.image_url,
            delivered_at=order.delivered_at,
        )
        for order, item in rows
    ]


@router.post("/reviews", response_model=ProductReviewRead, status_code=201)
def create_review_endpoint(
    payload: ProductReviewCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProductReviewRead:
    min_days, max_days = _get_review_window(db)
    review = create_review_for_order_item(db, current_user, payload, min_days=min_days, max_days=max_days)
    order = get_user_order(db, current_user, review.order_id)
    source_item = next((item for item in order.items if item.id == review.order_item_id), None)
    return _review_to_read(
        review,
        product_name=source_item.product_name if source_item else "Product",
        image_url=source_item.image_url if source_item else None,
    )


@router.get("/reviews", response_model=list[ProductReviewRead])
def list_reviews_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProductReviewRead]:
    reviews = list_user_reviews(db, current_user)
    order_ids = {review.order_id for review in reviews}
    order_map = {order.id: order for order in list_user_orders(db, current_user) if order.id in order_ids}
    response: list[ProductReviewRead] = []
    for review in reviews:
        order = order_map.get(review.order_id)
        source_item = next((item for item in order.items if item.id == review.order_item_id), None) if order else None
        response.append(
            _review_to_read(
                review,
                product_name=source_item.product_name if source_item else "Product",
                image_url=source_item.image_url if source_item else None,
            )
        )
    return response


@router.get("/notifications/reviews", response_model=ReviewNotificationRead)
def review_notifications_endpoint(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ReviewNotificationRead:
    sync_pending_review_notification(db, current_user)
    return ReviewNotificationRead(pending_count=get_pending_review_count(db, current_user))


@router.post("/orders/{order_id}/refund", response_model=OrderRead)
def request_refund_endpoint(
    order_id: uuid.UUID,
    payload: RefundRequestPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    from fastapi import HTTPException as _HTTPException, status as _status

    order = get_user_order(db, current_user, order_id)
    if order.refund_requested:
        raise _HTTPException(status_code=_status.HTTP_400_BAD_REQUEST, detail="Refund already requested for this order.")
    order.refund_requested = True
    order.refund_note = (payload.refund_note or "").strip() or None
    db.commit()
    db.refresh(order)
    return _order_to_read(order)
