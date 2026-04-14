import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.products import (
    create_product,
    get_product_or_404,
    list_products,
    soft_delete_product,
    update_product,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
def create_product_endpoint(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    product = create_product(db, payload)
    return ProductRead.model_validate(product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product_endpoint(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductRead:
    product = get_product_or_404(db, product_id)
    return ProductRead.model_validate(product)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product_endpoint(product_id: uuid.UUID, payload: ProductUpdate, db: Session = Depends(get_db)) -> ProductRead:
    product = get_product_or_404(db, product_id)
    updated = update_product(db, product, payload)
    return ProductRead.model_validate(updated)


@router.delete("/{product_id}", response_model=ProductRead)
def delete_product_endpoint(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductRead:
    product = get_product_or_404(db, product_id)
    updated = soft_delete_product(db, product)
    return ProductRead.model_validate(updated)


@router.get("", response_model=list[ProductRead])
def list_products_endpoint(
    category: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    products = list_products(db, category=category, active=active, search=q)
    return [ProductRead.model_validate(product) for product in products]
