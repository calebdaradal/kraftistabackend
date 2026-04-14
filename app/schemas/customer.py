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
    created_at: datetime
    items: list[OrderItemRead]
