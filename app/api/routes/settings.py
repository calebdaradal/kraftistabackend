from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.settings import SiteSetting
from app.models.user import User, UserRole
from app.schemas.settings import FaviconUploadResponse, LogoUploadResponse, SiteSettingsResponse, UpsertSiteSettingsRequest
from app.services.storage import download_bytes_from_uri, is_supabase_uri, upload_bytes

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY = "site"
ALLOWED_FAVICON_EXTS = {".ico", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
ALLOWED_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _upsert_settings(db: Session, data: Any, user_id: str | None) -> None:
    existing: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    if existing is None:
        db.add(SiteSetting(key=SETTINGS_KEY, data=data, updated_by=user_id))
        return
    existing.data = data  # type: ignore[assignment]
    existing.updated_by = user_id  # type: ignore[assignment]


def _public_asset_url(asset_kind: str, version: int | None) -> str:
    suffix = f"?v={version}" if version else ""
    return f"/api/settings/{asset_kind}{suffix}"


@router.get("", response_model=SiteSettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SiteSettingsResponse:
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    if not row:
        return SiteSettingsResponse(data=None)
    data = dict(row.data or {})
    if data.get("faviconPath"):
        data["faviconUrl"] = _public_asset_url("favicon", data.get("faviconVersion"))
    if data.get("logoPath"):
        data["logoUrl"] = _public_asset_url("logo", data.get("logoVersion"))
    return SiteSettingsResponse(data=data)


@router.put("", status_code=204)
def put_settings(
    payload: UpsertSiteSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    existing: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    merged = dict(existing.data) if existing and isinstance(existing.data, dict) else {}
    if isinstance(payload.data, dict):
        merged.update(payload.data)
    else:
        merged = payload.data
    _upsert_settings(db, merged, str(current_user.id))
    db.commit()


@router.post("/favicon", response_model=FaviconUploadResponse)
def upload_favicon(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> FaviconUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    ext = f".{file.filename.rsplit('.', 1)[1].lower()}" if "." in file.filename else ""
    if ext not in ALLOWED_FAVICON_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported favicon type. Allowed: {', '.join(sorted(ALLOWED_FAVICON_EXTS))}",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(content) > 2_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2MB).")

    settings = get_settings()
    storage_uri = upload_bytes(
        bucket=settings.supabase_bucket_web_settings,
        content=content,
        filename=file.filename,
        folder="favicon",
        content_type=file.content_type,
    )
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    current: dict[str, Any] = row.data if row else {}
    version = (current.get("faviconVersion") or 0) + 1
    current["faviconPath"] = storage_uri
    current["faviconVersion"] = version
    current["faviconUrl"] = _public_asset_url("favicon", version)
    _upsert_settings(db, current, str(current_user.id))
    db.commit()

    return FaviconUploadResponse(favicon_url=current["faviconUrl"])


@router.post("/logo", response_model=LogoUploadResponse)
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> LogoUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    ext = f".{file.filename.rsplit('.', 1)[1].lower()}" if "." in file.filename else ""
    if ext not in ALLOWED_LOGO_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported logo type. Allowed: {', '.join(sorted(ALLOWED_LOGO_EXTS))}",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(content) > 2_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2MB).")

    settings = get_settings()
    storage_uri = upload_bytes(
        bucket=settings.supabase_bucket_web_settings,
        content=content,
        filename=file.filename,
        folder="logo",
        content_type=file.content_type,
    )
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    current: dict[str, Any] = row.data if row else {}
    version = (current.get("logoVersion") or 0) + 1
    current["logoPath"] = storage_uri
    current["logoVersion"] = version
    current["logoUrl"] = _public_asset_url("logo", version)
    _upsert_settings(db, current, str(current_user.id))
    db.commit()

    return LogoUploadResponse(logo_url=current["logoUrl"])


def _content_type_from_uri(uri: str, fallback: str) -> str:
    parsed = urlparse(uri)
    path = parsed.path.lower()
    if path.endswith(".svg"):
        return "image/svg+xml"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".gif"):
        return "image/gif"
    if path.endswith(".ico"):
        return "image/x-icon"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    return fallback


@router.get("/logo")
def get_logo_asset(db: Session = Depends(get_db)) -> Response:
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    data = row.data if row else {}
    logo_path = data.get("logoPath")
    if not logo_path or not is_supabase_uri(logo_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo not configured.")
    content = download_bytes_from_uri(logo_path)
    return Response(
        content=content,
        media_type=_content_type_from_uri(logo_path, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/favicon")
def get_favicon_asset(db: Session = Depends(get_db)) -> Response:
    row: SiteSetting | None = db.query(SiteSetting).filter(SiteSetting.key == SETTINGS_KEY).one_or_none()
    data = row.data if row else {}
    favicon_path = data.get("faviconPath")
    if not favicon_path or not is_supabase_uri(favicon_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favicon not configured.")
    content = download_bytes_from_uri(favicon_path)
    return Response(
        content=content,
        media_type=_content_type_from_uri(favicon_path, "image/x-icon"),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )

