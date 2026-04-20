from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.settings import SiteSetting
from app.models.user import User, UserRole
from app.schemas.settings import FaviconUploadResponse, SiteSettingsResponse, UpsertSiteSettingsRequest

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY = "site"
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
FAVICON_BASENAME = "favicon"
ALLOWED_FAVICON_EXTS = {".ico", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _upsert_settings(db: Session, data: Any, user_id: str | None) -> None:
    existing: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    if existing is None:
        db.add(SiteSetting(key=SETTINGS_KEY, data=data, updated_by=user_id))
        return
    existing.data = data  # type: ignore[assignment]
    existing.updated_by = user_id  # type: ignore[assignment]


@router.get("", response_model=SiteSettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SiteSettingsResponse:
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    return SiteSettingsResponse(data=row.data if row else None)


@router.put("", status_code=204)
def put_settings(
    payload: UpsertSiteSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    _upsert_settings(db, payload.data, str(current_user.id))
    db.commit()


@router.post("/favicon", response_model=FaviconUploadResponse)
def upload_favicon(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> FaviconUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_FAVICON_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported favicon type. Allowed: {', '.join(sorted(ALLOWED_FAVICON_EXTS))}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / f"{FAVICON_BASENAME}{ext}"

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(content) > 2_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2MB).")

    target.write_bytes(content)

    # update settings.faviconUrl
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    current: dict[str, Any] = row.data if row else {}
    favicon_url = f"/uploads/{target.name}"
    current["faviconUrl"] = favicon_url
    _upsert_settings(db, current, str(current_user.id))
    db.commit()

    return FaviconUploadResponse(favicon_url=favicon_url)

