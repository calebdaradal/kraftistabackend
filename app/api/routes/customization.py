from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.customization import SiteCustomization
from app.models.user import User, UserRole
from app.schemas.customization import SiteCustomizationResponse, UpsertCustomizationRequest
from app.services.storage import download_bytes_from_uri, is_supabase_uri, upload_bytes
from app.core.config import get_settings as get_app_config

router = APIRouter(prefix="/customization", tags=["customization"])

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _upsert_customization(db: Session, key: str, data: object, user_id: str | None) -> None:
    existing: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == key).one_or_none()
    )
    if existing is None:
        db.add(SiteCustomization(key=key, data=data, updated_by=user_id))
        return
    existing.data = dict(data) if isinstance(data, dict) else data  # type: ignore[assignment]
    existing.updated_by = user_id  # type: ignore[assignment]
    flag_modified(existing, "data")


def _content_type_from_path(path: str, fallback: str) -> str:
    p = urlparse(path).path.lower()
    if p.endswith(".svg"):
        return "image/svg+xml"
    if p.endswith(".webp"):
        return "image/webp"
    if p.endswith(".png"):
        return "image/png"
    if p.endswith(".gif"):
        return "image/gif"
    if p.endswith(".jpg") or p.endswith(".jpeg"):
        return "image/jpeg"
    return fallback


@router.get("", response_model=SiteCustomizationResponse)
def get_site_customization(db: Session = Depends(get_db)) -> SiteCustomizationResponse:
    rows = (
        db.query(SiteCustomization)
        .filter(SiteCustomization.key.in_(["about", "footer", "hero"]))
        .all()
    )
    data_by_key = {row.key: row.data for row in rows}
    return SiteCustomizationResponse(
        about=data_by_key.get("about"),
        footer=data_by_key.get("footer"),
        hero=data_by_key.get("hero"),
    )


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


@router.put("/hero", status_code=204)
def put_hero_customization(
    payload: UpsertCustomizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    _upsert_customization(db, "hero", payload.data, str(current_user.id))
    db.commit()


@router.post("/about/preview-image")
def upload_about_preview_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    ext = f".{file.filename.rsplit('.', 1)[1].lower()}" if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTS))}",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(content) > 5_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5MB).")

    settings = get_app_config()
    storage_uri = upload_bytes(
        bucket=settings.supabase_bucket_web_settings,
        content=content,
        filename=file.filename,
        folder="about",
        content_type=file.content_type,
    )

    # Persist the URI into the about customization row
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "about").one_or_none()
    )
    current: dict = dict(row.data) if row else {}
    current["previewImage"] = storage_uri
    current["previewImageUrl"] = f"/api/customization/about/preview-image"
    _upsert_customization(db, "about", current, str(current_user.id))
    db.commit()

    return {"preview_image_url": "/api/customization/about/preview-image"}


@router.get("/about/preview-image")
def get_about_preview_image(db: Session = Depends(get_db)) -> Response:
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "about").one_or_none()
    )
    data = row.data if row else {}
    image_path = data.get("previewImage") if isinstance(data, dict) else None
    if not image_path or not is_supabase_uri(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview image not configured.")
    content = download_bytes_from_uri(image_path)
    return Response(
        content=content,
        media_type=_content_type_from_path(image_path, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )
