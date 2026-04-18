import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.customer import ProductReviewRead
from app.schemas.orders import (
    SellerOrderRead,
    SellerOrderStatusUpdate,
    SellerOrderTrackingUpdate,
    SellerReviewModerationUpdate,
)
from app.services.orders import (
    get_order_or_404,
    list_orders_fifo,
    list_reviews_for_moderation,
    moderate_review,
    update_order_status,
    update_order_tracking,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_to_read(order) -> SellerOrderRead:
    return SellerOrderRead(
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
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "image_url": item.image_url,
                "quantity": item.quantity,
                "selected_variations": item.selected_variations,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in order.items
        ],
    )


@router.get("", response_model=list[SellerOrderRead])
def list_orders_endpoint(
    db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin, UserRole.editor))
) -> list[SellerOrderRead]:
    return [_order_to_read(order) for order in list_orders_fifo(db)]


@router.get("/{order_id}", response_model=SellerOrderRead)
def get_order_endpoint(
    order_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin, UserRole.editor))
) -> SellerOrderRead:
    return _order_to_read(get_order_or_404(db, order_id))


@router.patch("/{order_id}/tracking", response_model=SellerOrderRead)
def update_order_tracking_endpoint(
    order_id: uuid.UUID,
    payload: SellerOrderTrackingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> SellerOrderRead:
    order = get_order_or_404(db, order_id)
    return _order_to_read(update_order_tracking(db, order, payload.tracking_reference))


@router.patch("/{order_id}/status", response_model=SellerOrderRead)
def update_order_status_endpoint(
    order_id: uuid.UUID,
    payload: SellerOrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> SellerOrderRead:
    order = get_order_or_404(db, order_id)
    return _order_to_read(update_order_status(db, order, payload.status))


@router.patch("/reviews/{review_id}", response_model=ProductReviewRead)
def moderate_review_endpoint(
    review_id: uuid.UUID,
    payload: SellerReviewModerationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> ProductReviewRead:
    review = moderate_review(db, review_id, current_user, payload.moderation_status, payload.moderation_note)
    order = get_order_or_404(db, review.order_id)
    source_item = next((item for item in order.items if item.id == review.order_item_id), None)
    return ProductReviewRead(
        id=review.id,
        order_id=review.order_id,
        order_item_id=review.order_item_id,
        product_id=review.product_id,
        product_name=source_item.product_name if source_item else "Product",
        image_url=source_item.image_url if source_item else None,
        rating=review.rating,
        comment=review.comment,
        moderation_status=review.moderation_status,
        moderation_note=review.moderation_note,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.get("/reviews/list", response_model=list[ProductReviewRead])
def list_reviews_endpoint(
    moderation_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> list[ProductReviewRead]:
    reviews = list_reviews_for_moderation(db, moderation_status)
    response: list[ProductReviewRead] = []
    for review in reviews:
        order = get_order_or_404(db, review.order_id)
        source_item = next((item for item in order.items if item.id == review.order_item_id), None)
        response.append(
            ProductReviewRead(
                id=review.id,
                order_id=review.order_id,
                order_item_id=review.order_item_id,
                product_id=review.product_id,
                product_name=source_item.product_name if source_item else "Product",
                image_url=source_item.image_url if source_item else None,
                rating=review.rating,
                comment=review.comment,
                moderation_status=review.moderation_status,
                moderation_note=review.moderation_note,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )
        )
    return response
