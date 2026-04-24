import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)
    selected_variations: dict[str, str] = Field(default_factory=dict)
    unit_price: Decimal = Field(ge=0)
    image_url: str | None = None
    product_name: str


class CartItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    selected_variations: dict[str, str]
    unit_price: Decimal
    image_url: str | None
    product_name: str


class CartRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    items: list[CartItemRead]


class CheckoutRequest(BaseModel):
    payment_method: str = "card"
    order_note: str | None = None
    shipping_address: dict[str, str]


class OrderItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    selected_variations: dict[str, str]
    unit_price: Decimal
    line_total: Decimal
    product_name: str
    image_url: str | None


class OrderRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal
    payment_method: str
    order_note: str | None
    shipping_address: dict[str, str]
    tracking_reference: str | None
    delivered_at: datetime | None
    created_at: datetime
    refund_requested: bool = False
    refund_note: str | None = None
    items: list[OrderItemRead]


class ProductLikeRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    created_at: datetime


class ProductLikeCreate(BaseModel):
    product_id: uuid.UUID


class PendingReviewItemRead(BaseModel):
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    image_url: str | None
    delivered_at: datetime | None


class ProductReviewCreate(BaseModel):
    order_item_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ProductReviewRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    image_url: str | None
    rating: int
    comment: str | None
    moderation_status: str
    moderation_note: str | None
    created_at: datetime
    updated_at: datetime


class ReviewNotificationRead(BaseModel):
    pending_count: int
