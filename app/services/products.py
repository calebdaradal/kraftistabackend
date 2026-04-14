import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def _apply_product_filters(
    query: Select[tuple[Product]], category: str | None, active: bool | None, search: str | None
) -> Select[tuple[Product]]:
    if category:
        query = query.where(Product.category == category)
    if active is not None:
        query = query.where(Product.active == active)
    if search:
        query = query.where(
            or_(Product.name.ilike(f"%{search}%"), Product.sku.ilike(f"%{search}%"), Product.full_description.ilike(f"%{search}%"))
        )
    return query


def create_product(db: Session, payload: ProductCreate) -> Product:
    if db.scalar(select(Product).where(Product.sku == payload.sku)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists.")

    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    update_data = payload.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.scalar(select(Product).where(Product.sku == update_data["sku"]))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists.")

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


def list_products(db: Session, category: str | None, active: bool | None, search: str | None) -> list[Product]:
    query = select(Product).order_by(Product.created_at.desc())
    query = _apply_product_filters(query, category, active, search)
    return list(db.scalars(query).all())


def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
