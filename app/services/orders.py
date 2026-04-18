import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.engagement import ProductReview
from app.models.order import Order
from app.models.user import User


def list_orders_fifo(db: Session) -> list[Order]:
    return list(db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.created_at.asc())).all())


def get_order_or_404(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


def update_order_tracking(db: Session, order: Order, tracking_reference: str | None) -> Order:
    order.tracking_reference = (tracking_reference or "").strip() or None
    db.commit()
    db.refresh(order)
    return order


def update_order_status(db: Session, order: Order, status_value: str) -> Order:
    order.status = status_value
    if status_value == "delivered":
        order.delivered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


def moderate_review(
    db: Session, review_id: uuid.UUID, moderator: User, moderation_status: str, moderation_note: str | None
) -> ProductReview:
    review = db.get(ProductReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    review.moderation_status = moderation_status
    review.moderation_note = moderation_note
    review.moderated_by = moderator.id
    review.moderated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def list_reviews_for_moderation(db: Session, status_value: str | None = None) -> list[ProductReview]:
    query = select(ProductReview).order_by(ProductReview.created_at.asc())
    if status_value:
        query = query.where(ProductReview.moderation_status == status_value)
    return list(db.scalars(query).all())
