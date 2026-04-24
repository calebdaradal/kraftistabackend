import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.engagement import ProductReview
from app.schemas.product import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    PublicReviewRead,
    TagCreate,
    TagRead,
    TagUpdate,
    TaxonomyDeleteImpact,
)
from app.services.products import (
    count_products_for_category,
    count_products_for_tag,
    create_category,
    create_product,
    create_tag,
    delete_category,
    delete_product,
    delete_tag,
    get_product_or_404,
    list_categories_with_counts,
    list_products,
    list_tags_with_counts,
    serialize_product,
    update_category,
    update_product,
    update_tag,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
def create_product_endpoint(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> ProductRead:
    product = create_product(db, payload)
    return ProductRead.model_validate(serialize_product(product))


@router.get("", response_model=list[ProductRead])
def list_products_endpoint(
    category: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    featured: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    products = list_products(db, category=category, active=active, search=q, featured=featured)
    return [ProductRead.model_validate(serialize_product(product)) for product in products]


@router.get("/categories", response_model=list[CategoryRead])
def list_categories_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> list[CategoryRead]:
    rows = list_categories_with_counts(db)
    return [
        CategoryRead.model_validate(
            {
                "id": row.category.id,
                "name": row.category.name,
                "slug": row.category.slug,
                "product_count": row.product_count,
                "created_at": row.category.created_at,
                "updated_at": row.category.updated_at,
            }
        )
        for row in rows
    ]


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category_endpoint(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> CategoryRead:
    category = create_category(db, payload.name)
    return CategoryRead.model_validate(
        {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "product_count": 0,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
    )


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category_endpoint(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> CategoryRead:
    category = update_category(db, category_id, payload.name)
    return CategoryRead.model_validate(
        {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "product_count": count_products_for_category(db, category_id),
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
    )


@router.get("/categories/{category_id}/impact", response_model=TaxonomyDeleteImpact)
def category_delete_impact_endpoint(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> TaxonomyDeleteImpact:
    return TaxonomyDeleteImpact(product_count=count_products_for_category(db, category_id))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_endpoint(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> Response:
    delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tags", response_model=list[TagRead])
def list_tags_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> list[TagRead]:
    rows = list_tags_with_counts(db)
    return [
        TagRead.model_validate(
            {
                "id": row.tag.id,
                "name": row.tag.name,
                "slug": row.tag.slug,
                "product_count": row.product_count,
                "created_at": row.tag.created_at,
                "updated_at": row.tag.updated_at,
            }
        )
        for row in rows
    ]


@router.post("/tags", response_model=TagRead, status_code=201)
def create_tag_endpoint(
    payload: TagCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> TagRead:
    tag = create_tag(db, payload.name)
    return TagRead.model_validate(
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "product_count": 0,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
        }
    )


@router.patch("/tags/{tag_id}", response_model=TagRead)
def update_tag_endpoint(
    tag_id: uuid.UUID,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> TagRead:
    tag = update_tag(db, tag_id, payload.name)
    return TagRead.model_validate(
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "product_count": count_products_for_tag(db, tag_id),
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
        }
    )


@router.get("/tags/{tag_id}/impact", response_model=TaxonomyDeleteImpact)
def tag_delete_impact_endpoint(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> TaxonomyDeleteImpact:
    return TaxonomyDeleteImpact(product_count=count_products_for_tag(db, tag_id))


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_endpoint(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> Response:
    delete_tag(db, tag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{product_id}/reviews", response_model=list[PublicReviewRead])
def list_product_reviews_endpoint(
    product_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[PublicReviewRead]:
    from sqlalchemy import select as _select

    offset = (page - 1) * limit
    rows = list(
        db.scalars(
            _select(ProductReview)
            .where(ProductReview.product_id == product_id, ProductReview.moderation_status == "approved")
            .order_by(ProductReview.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [PublicReviewRead(id=r.id, rating=r.rating, comment=r.comment, created_at=r.created_at) for r in rows]


@router.get("/{product_id}", response_model=ProductRead)
def get_product_endpoint(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductRead:
    product = get_product_or_404(db, product_id)
    return ProductRead.model_validate(serialize_product(product))


@router.patch("/{product_id}", response_model=ProductRead)
def update_product_endpoint(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> ProductRead:
    product = get_product_or_404(db, product_id)
    updated = update_product(db, product, payload)
    return ProductRead.model_validate(serialize_product(updated))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_endpoint(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> Response:
    product = get_product_or_404(db, product_id)
    delete_product(db, product)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
