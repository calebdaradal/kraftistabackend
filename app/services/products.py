import uuid
from dataclasses import dataclass
from re import sub

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Category, Product, Tag
from app.schemas.product import ProductCreate, ProductUpdate


@dataclass
class CategoryWithCount:
    category: Category
    product_count: int


@dataclass
class TagWithCount:
    tag: Tag
    product_count: int


def _slugify(value: str) -> str:
    normalized = sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "item"


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty.")
    return normalized


def _resolve_category(db: Session, category_name: str | None) -> Category | None:
    if category_name is None:
        return None
    if not category_name.strip():
        return None
    normalized = _normalize_name(category_name)
    return db.scalar(select(Category).where(func.lower(Category.name) == normalized.lower()))


def _get_or_create_tags(db: Session, tag_names: list[str] | None) -> list[Tag]:
    if not tag_names:
        return []

    deduped: dict[str, str] = {}
    for raw in tag_names:
        normalized = _normalize_name(raw)
        deduped[normalized.lower()] = normalized

    resolved: list[Tag] = []
    for _, normalized in deduped.items():
        existing = db.scalar(select(Tag).where(func.lower(Tag.name) == normalized.lower()))
        if existing:
            resolved.append(existing)
            continue
        tag = Tag(name=normalized, slug=_slugify(normalized))
        db.add(tag)
        db.flush()
        resolved.append(tag)
    return resolved


def serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "short_description": product.short_description,
        "full_description": product.full_description,
        "category": product.category_ref.name if product.category_ref else None,
        "featured": product.featured,
        "active": product.active,
        "price": product.price,
        "original_price": product.original_price,
        "in_stock": product.in_stock,
        "stock_count": product.stock_count,
        "image_url": product.image_url,
        "gallery_urls": product.gallery_urls,
        "tags": [tag.name for tag in product.tags_ref],
        "rating": product.rating,
        "review_count": product.review_count,
        "dimension_width_cm": product.dimension_width_cm,
        "dimension_height_cm": product.dimension_height_cm,
        "dimension_length_cm": product.dimension_length_cm,
        "weight_kg": product.weight_kg,
        "materials": product.materials,
        "care_instructions": product.care_instructions,
        "primary_variation": product.primary_variation,
        "secondary_variation": product.secondary_variation,
        "tertiary_variation": product.tertiary_variation,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def _apply_product_filters(
    query: Select[tuple[Product]], category: str | None, active: bool | None, search: str | None, featured: bool | None
) -> Select[tuple[Product]]:
    if category:
        query = query.join(Product.category_ref).where(func.lower(Category.name) == category.strip().lower())
    if active is not None:
        query = query.where(Product.active == active)
    if featured is not None:
        query = query.where(Product.featured == featured)
    if search:
        query = query.where(
            or_(Product.name.ilike(f"%{search}%"), Product.sku.ilike(f"%{search}%"), Product.full_description.ilike(f"%{search}%"))
        )
    return query


def create_product(db: Session, payload: ProductCreate) -> Product:
    if db.scalar(select(Product).where(Product.sku == payload.sku)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists.")

    values = payload.model_dump()
    tag_names = values.pop("tags", None)
    category_name = values.pop("category", None)
    product = Product(**values)
    product.category_ref = _resolve_category(db, category_name)
    product.tags_ref = _get_or_create_tags(db, tag_names)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.category_ref), selectinload(Product.tags_ref))
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    update_data = payload.model_dump(exclude_unset=True)
    tag_names = update_data.pop("tags", None) if "tags" in update_data else None
    category_name = update_data.pop("category", None) if "category" in update_data else None

    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.scalar(select(Product).where(Product.sku == update_data["sku"]))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists.")

    for key, value in update_data.items():
        setattr(product, key, value)
    if category_name is not None:
        product.category_ref = _resolve_category(db, category_name)
    if tag_names is not None:
        product.tags_ref = _get_or_create_tags(db, tag_names)

    db.commit()
    db.refresh(product)
    return product


def list_products(
    db: Session, category: str | None, active: bool | None, search: str | None, featured: bool | None
) -> list[Product]:
    query = select(Product).options(selectinload(Product.category_ref), selectinload(Product.tags_ref)).order_by(Product.created_at.desc())
    query = _apply_product_filters(query, category, active, search, featured)
    return list(db.scalars(query).all())


def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()


def list_categories_with_counts(db: Session) -> list[CategoryWithCount]:
    rows = db.execute(
        select(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name.asc())
    ).all()
    return [CategoryWithCount(category=row[0], product_count=int(row[1])) for row in rows]


def create_category(db: Session, name: str) -> Category:
    normalized = _normalize_name(name)
    existing = db.scalar(select(Category).where(func.lower(Category.name) == normalized.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists.")
    category = Category(name=normalized, slug=_slugify(normalized))
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: uuid.UUID, name: str) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    normalized = _normalize_name(name)
    existing = db.scalar(select(Category).where(func.lower(Category.name) == normalized.lower(), Category.id != category_id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists.")
    category.name = normalized
    category.slug = _slugify(normalized)
    db.commit()
    db.refresh(category)
    return category


def count_products_for_category(db: Session, category_id: uuid.UUID) -> int:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return int(db.scalar(select(func.count(Product.id)).where(Product.category_id == category_id)) or 0)


def delete_category(db: Session, category_id: uuid.UUID) -> None:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    db.query(Product).filter(Product.category_id == category_id).update({Product.category_id: None}, synchronize_session=False)
    db.delete(category)
    db.commit()


def list_tags_with_counts(db: Session) -> list[TagWithCount]:
    rows = db.execute(
        select(Tag, func.count(Product.id).label("product_count"))
        .outerjoin(Tag.products)
        .group_by(Tag.id)
        .order_by(Tag.name.asc())
    ).all()
    return [TagWithCount(tag=row[0], product_count=int(row[1])) for row in rows]


def create_tag(db: Session, name: str) -> Tag:
    normalized = _normalize_name(name)
    existing = db.scalar(select(Tag).where(func.lower(Tag.name) == normalized.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists.")
    tag = Tag(name=normalized, slug=_slugify(normalized))
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: uuid.UUID, name: str) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    normalized = _normalize_name(name)
    existing = db.scalar(select(Tag).where(func.lower(Tag.name) == normalized.lower(), Tag.id != tag_id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists.")
    tag.name = normalized
    tag.slug = _slugify(normalized)
    db.commit()
    db.refresh(tag)
    return tag


def count_products_for_tag(db: Session, tag_id: uuid.UUID) -> int:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    count = db.execute(
        select(func.count(Product.id)).join(Product.tags_ref).where(Tag.id == tag_id)
    ).scalar_one()
    return int(count)


def delete_tag(db: Session, tag_id: uuid.UUID) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    db.delete(tag)
    db.commit()
