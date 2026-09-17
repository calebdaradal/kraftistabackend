import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _reject_data_url(value: str) -> str:
    if value.lstrip().lower().startswith("data:"):
        raise ValueError("Data URLs are not supported for images.")
    return value


def _reject_data_urls_in_variation(value: object) -> object:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "image" and isinstance(item, str):
                _reject_data_url(item)
            else:
                _reject_data_urls_in_variation(item)
    elif isinstance(value, list):
        for item in value:
            _reject_data_urls_in_variation(item)
    return value


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=100)
    short_description: str | None = None
    full_description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    collection: str | None = Field(default=None, max_length=120)
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

    @field_validator("image_url")
    @classmethod
    def reject_image_data_url(cls, value: str | None) -> str | None:
        return _reject_data_url(value) if value is not None else value

    @field_validator("gallery_urls")
    @classmethod
    def reject_gallery_data_urls(cls, value: list[str] | None) -> list[str] | None:
        return [_reject_data_url(item) for item in value] if value is not None else value

    @field_validator("primary_variation", "secondary_variation", "tertiary_variation")
    @classmethod
    def reject_variation_image_data_urls(cls, value: dict | None) -> dict | None:
        return _reject_data_urls_in_variation(value) if value is not None else value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    short_description: str | None = None
    full_description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    collection: str | None = Field(default=None, max_length=120)
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

    @field_validator("image_url")
    @classmethod
    def reject_image_data_url(cls, value: str | None) -> str | None:
        return _reject_data_url(value) if value is not None else value

    @field_validator("gallery_urls")
    @classmethod
    def reject_gallery_data_urls(cls, value: list[str] | None) -> list[str] | None:
        return [_reject_data_url(item) for item in value] if value is not None else value

    @field_validator("primary_variation", "secondary_variation", "tertiary_variation")
    @classmethod
    def reject_variation_image_data_urls(cls, value: dict | None) -> dict | None:
        return _reject_data_urls_in_variation(value) if value is not None else value


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sku: str
    short_description: str | None
    full_description: str | None
    category: str | None
    collection: str | None
    featured: bool
    active: bool
    price: Decimal
    original_price: Decimal | None
    in_stock: bool
    stock_count: int
    image_url: str | None
    image_storage_uri: str | None = None
    gallery_urls: list[str] | None
    gallery_storage_uris: list[str | None] | None = None
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
    primary_variation_storage: dict | None = None
    secondary_variation: dict | None
    secondary_variation_storage: dict | None = None
    tertiary_variation: dict | None
    tertiary_variation_storage: dict | None = None
    created_at: datetime
    updated_at: datetime


class TaxonomyBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryCreate(TaxonomyBase):
    image_url: str | None = None
    description: str | None = None

    @field_validator("image_url")
    @classmethod
    def reject_image_data_url(cls, value: str | None) -> str | None:
        return _reject_data_url(value) if value is not None else value


class CategoryUpdate(TaxonomyBase):
    image_url: str | None = None
    description: str | None = None

    @field_validator("image_url")
    @classmethod
    def reject_image_data_url(cls, value: str | None) -> str | None:
        return _reject_data_url(value) if value is not None else value


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None = None
    image_storage_uri: str | None = None
    description: str | None = None
    product_count: int
    created_at: datetime
    updated_at: datetime


class PublicCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    product_count: int


class CollectionCreate(TaxonomyBase):
    pass


class CollectionUpdate(TaxonomyBase):
    pass


class CollectionRead(BaseModel):
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
