import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SellerOrderItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    image_url: str | None
    quantity: int
    selected_variations: dict[str, str]
    unit_price: Decimal
    line_total: Decimal


class SellerOrderRead(BaseModel):
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
    items: list[SellerOrderItemRead]


class RefundRequestPayload(BaseModel):
    refund_note: str | None = Field(default=None, max_length=1000)


class SellerOrderTrackingUpdate(BaseModel):
    tracking_reference: str | None = Field(default=None, max_length=255)


class SellerOrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(processing|shipped|delivered)$")


class SellerReviewModerationUpdate(BaseModel):
    moderation_status: str = Field(pattern="^(approved|rejected)$")
    moderation_note: str | None = None
