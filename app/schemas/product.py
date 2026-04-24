import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=100)
    short_description: str | None = None
    full_description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    featured: bool = False
    active: bool = True
    price: Decimal = Field(ge=0)
    original_price: Decimal | None = Field(default=None, ge=0)
    in_stock: bool = True
    stock_count: int = Field(default=0, ge=0)
    image_url: str | None = None
    gallery_urls: list[str] | None = None
    tags: list[str] | None = None
    rating: Decimal = Field(default=0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    dimension_width_cm: Decimal | None = Field(default=None, ge=0)
    dimension_height_cm: Decimal | None = Field(default=None, ge=0)
    dimension_length_cm: Decimal | None = Field(default=None, ge=0)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    materials: list[str] | None = None
    care_instructions: list[str] | None = None
    primary_variation: dict | None = None
    secondary_variation: dict | None = None
    tertiary_variation: dict | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    short_description: str | None = None
    full_description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    featured: bool | None = None
    active: bool | None = None
    price: Decimal | None = Field(default=None, ge=0)
    original_price: Decimal | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    stock_count: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    gallery_urls: list[str] | None = None
    tags: list[str] | None = None
    rating: Decimal | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    dimension_width_cm: Decimal | None = Field(default=None, ge=0)
    dimension_height_cm: Decimal | None = Field(default=None, ge=0)
    dimension_length_cm: Decimal | None = Field(default=None, ge=0)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    materials: list[str] | None = None
    care_instructions: list[str] | None = None
    primary_variation: dict | None = None
    secondary_variation: dict | None = None
    tertiary_variation: dict | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sku: str
    short_description: str | None
    full_description: str | None
    category: str | None
    featured: bool
    active: bool
    price: Decimal
    original_price: Decimal | None
    in_stock: bool
    stock_count: int
    image_url: str | None
    gallery_urls: list[str] | None
    tags: list[str] | None
    rating: Decimal
    review_count: int
    dimension_width_cm: Decimal | None
    dimension_height_cm: Decimal | None
    dimension_length_cm: Decimal | None
    weight_kg: Decimal | None
    materials: list[str] | None
    care_instructions: list[str] | None
    primary_variation: dict | None
    secondary_variation: dict | None
    tertiary_variation: dict | None
    created_at: datetime
    updated_at: datetime


class TaxonomyBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryCreate(TaxonomyBase):
    pass


class CategoryUpdate(TaxonomyBase):
    pass


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    product_count: int
    created_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class TagUpdate(TagCreate):
    pass


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    product_count: int
    created_at: datetime
    updated_at: datetime


class TaxonomyDeleteImpact(BaseModel):
    product_count: int


class PublicReviewRead(BaseModel):
    id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
