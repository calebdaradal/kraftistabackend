from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.customization import SiteCustomization
from app.models.user import User, UserRole
from app.schemas.customization import SiteCustomizationResponse, UpsertCustomizationRequest

router = APIRouter(prefix="/customization", tags=["customization"])


@router.get("", response_model=SiteCustomizationResponse)
def get_site_customization(db: Session = Depends(get_db)) -> SiteCustomizationResponse:
    rows = (
        db.query(SiteCustomization)
        .filter(SiteCustomization.key.in_(["about", "footer"]))
        .all()
    )
    data_by_key = {row.key: row.data for row in rows}
    return SiteCustomizationResponse(
        about=data_by_key.get("about"),
        footer=data_by_key.get("footer"),
    )


def _upsert_customization(db: Session, key: str, data: object, user_id: str | None) -> None:
    existing: SiteCustomization | None = db.query(SiteCustomization).filter(SiteCustomization.key == key).one_or_none()
    if existing is None:
        db.add(SiteCustomization(key=key, data=data, updated_by=user_id))
        return
    existing.data = data  # type: ignore[assignment]
    existing.updated_by = user_id  # type: ignore[assignment]


@router.put("/about", status_code=204)
def put_about_customization(
    payload: UpsertCustomizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    _upsert_customization(db, "about", payload.data, str(current_user.id))
    db.commit()


@router.put("/footer", status_code=204)
def put_footer_customization(
    payload: UpsertCustomizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    _upsert_customization(db, "footer", payload.data, str(current_user.id))
    db.commit()

