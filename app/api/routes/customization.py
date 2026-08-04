from __future__ import annotations

import copy
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.customization import SiteCustomization
from app.models.user import User, UserRole
from app.schemas.customization import SiteCustomizationResponse, UpsertCustomizationRequest
from app.services.storage import delete_file_from_uri, download_bytes_from_uri, is_supabase_uri, upload_bytes
from app.core.config import get_settings as get_app_config

router = APIRouter(prefix="/customization", tags=["customization"])

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _services_collect_sb_uris(services: object) -> set[str]:
    uris: set[str] = set()
    if not isinstance(services, dict):
        return uris
    img = services.get("image")
    if img and isinstance(img, str) and is_supabase_uri(img):
        uris.add(img)
    bullets = services.get("bullets")
    if not isinstance(bullets, list):
        return uris
    for b in bullets:
        if not isinstance(b, dict):
            continue
        for key in ("bulletImage", "carouselImage"):
            v = b.get(key)
            if v and isinstance(v, str) and is_supabase_uri(v):
                uris.add(v)
    return uris


def _bullet_merge_media(stored: dict | None, incoming: dict | None) -> None:
    if not stored or not incoming:
        return
    for key in ("bulletImage", "carouselImage"):
        s = stored.get(key)
        inc = incoming.get(key)
        if s and isinstance(s, str) and is_supabase_uri(s):
            if not inc or not isinstance(inc, str) or not is_supabase_uri(inc):
                incoming[key] = s


def _merge_services_media_from_stored(stored: dict | None, merged: dict) -> None:
    if not isinstance(merged, dict):
        return
    if isinstance(stored, dict):
        stored_image = stored.get("image")
        incoming_image = merged.get("image")
        if stored_image and isinstance(stored_image, str) and is_supabase_uri(stored_image):
            if not incoming_image or not isinstance(incoming_image, str) or not is_supabase_uri(incoming_image):
                merged["image"] = stored_image

    bullets_in = merged.get("bullets")
    if not isinstance(bullets_in, list):
        return
    by_id: dict[str, dict] = {}
    sb = stored.get("bullets") if isinstance(stored, dict) else None
    if isinstance(sb, list):
        for b in sb:
            if isinstance(b, dict) and b.get("id") is not None:
                by_id[str(b["id"])] = b

    for b in bullets_in:
        if isinstance(b, dict) and b.get("id") is not None:
            sid = str(b["id"])
            if sid in by_id:
                _bullet_merge_media(by_id[sid], b)


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
        .filter(SiteCustomization.key.in_(["about", "footer", "hero", "services"]))
        .all()
    )
    data_by_key = {row.key: row.data for row in rows}
    return SiteCustomizationResponse(
        about=data_by_key.get("about"),
        footer=data_by_key.get("footer"),
        hero=data_by_key.get("hero"),
        services=data_by_key.get("services"),
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
    incoming = dict(payload.data) if isinstance(payload.data, dict) else {}
    existing: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "hero").one_or_none()
    )
    stored = dict(existing.data) if existing and isinstance(existing.data, dict) else {}
    stored_image = stored.get("image")
    if stored_image and is_supabase_uri(str(stored_image)) and not incoming.get("image"):
        incoming["image"] = stored_image
        incoming["imageUrl"] = "/api/customization/hero/image"
    _upsert_customization(db, "hero", incoming, str(current_user.id))
    db.commit()


@router.post("/hero/image")
def upload_hero_image(
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

    config = get_app_config()
    storage_uri = upload_bytes(
        bucket=config.supabase_bucket_web_settings,
        content=content,
        filename=file.filename,
        folder="hero",
        content_type=file.content_type,
    )
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "hero").one_or_none()
    )
    current = dict(row.data) if row and isinstance(row.data, dict) else {}
    old_uri = current.get("image")
    if old_uri and is_supabase_uri(str(old_uri)):
        delete_file_from_uri(str(old_uri))

    current["image"] = storage_uri
    current["imageUrl"] = "/api/customization/hero/image"
    current.setdefault("imageAlt", "Kraftista handcrafted and personalized gifts")
    _upsert_customization(db, "hero", current, str(current_user.id))
    db.commit()
    return {"image_url": current["imageUrl"], "image": storage_uri}


@router.get("/hero/image")
def get_hero_image(db: Session = Depends(get_db)) -> Response:
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "hero").one_or_none()
    )
    data = row.data if row else {}
    image_path = data.get("image") if isinstance(data, dict) else None
    if not image_path or not is_supabase_uri(str(image_path)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hero image not configured.")
    image_uri = str(image_path)
    content = download_bytes_from_uri(image_uri)
    return Response(
        content=content,
        media_type=_content_type_from_path(image_uri, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/hero/image", status_code=204)
def delete_hero_image(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "hero").one_or_none()
    )
    current = dict(row.data) if row and isinstance(row.data, dict) else {}
    old_uri = current.get("image")
    if old_uri and is_supabase_uri(str(old_uri)):
        delete_file_from_uri(str(old_uri))
    current.pop("image", None)
    current["imageUrl"] = "/HeaderImage.png"
    current.setdefault("imageAlt", "Kraftista handcrafted and personalized gifts")
    _upsert_customization(db, "hero", current, str(current_user.id))
    db.commit()


@router.put("/services", status_code=204)
def put_services_customization(
    payload: UpsertCustomizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    raw = payload.data if isinstance(payload.data, dict) else payload.data
    incoming: dict = copy.deepcopy(dict(raw)) if isinstance(raw, dict) else {}
    existing: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "services").one_or_none()
    )
    stored: dict | None = dict(existing.data) if existing and isinstance(existing.data, dict) else None

    old_uris = _services_collect_sb_uris(stored)
    _merge_services_media_from_stored(stored, incoming)
    new_uris = _services_collect_sb_uris(incoming)
    for orphan in old_uris - new_uris:
        delete_file_from_uri(orphan)

    _upsert_customization(db, "services", incoming, str(current_user.id))
    db.commit()


def _services_row(db: Session) -> dict:
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "services").one_or_none()
    )
    return dict(row.data) if row and isinstance(row.data, dict) else {}


def _find_bullet(services_data: dict, bullet_id: str) -> tuple[int, dict | None]:
    bullets = services_data.get("bullets")
    if not isinstance(bullets, list):
        return -1, None
    for i, b in enumerate(bullets):
        if isinstance(b, dict) and str(b.get("id")) == str(bullet_id):
            return i, b
    return -1, None


def _persist_services(db: Session, data: dict, user_id: str) -> None:
    _upsert_customization(db, "services", data, user_id)
    db.commit()


@router.delete("/services/bullet/{bullet_id}")
def delete_services_bullet(
    bullet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    current = _services_row(db)
    idx, bullet = _find_bullet(current, bullet_id)
    if idx < 0 or not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")

    for key in ("bulletImage", "carouselImage"):
        uri = bullet.get(key)
        if uri and isinstance(uri, str) and is_supabase_uri(uri):
            delete_file_from_uri(uri)

    bullets = current.get("bullets")
    if isinstance(bullets, list):
        bullets.pop(idx)

    current["bullets"] = bullets
    _persist_services(db, current, str(current_user.id))


@router.post("/services/image")
def upload_services_image(
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
        folder="services",
        content_type=file.content_type,
    )

    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "services").one_or_none()
    )
    current: dict = dict(row.data) if row else {}

    # Delete the previously stored file before replacing the reference.
    old_uri = current.get("image")
    if old_uri and is_supabase_uri(old_uri):
        delete_file_from_uri(old_uri)

    current["image"] = storage_uri
    current["imageUrl"] = "/api/customization/services/image"
    _upsert_customization(db, "services", current, str(current_user.id))
    db.commit()

    return {"image_url": "/api/customization/services/image"}


@router.get("/services/image")
def get_services_image(db: Session = Depends(get_db)) -> Response:
    row: SiteCustomization | None = (
        db.query(SiteCustomization).filter(SiteCustomization.key == "services").one_or_none()
    )
    data = row.data if row else {}
    image_path = data.get("image") if isinstance(data, dict) else None
    if not image_path or not is_supabase_uri(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Services image not configured.")
    content = download_bytes_from_uri(image_path)
    return Response(
        content=content,
        media_type=_content_type_from_path(image_path, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


def _bullet_image_upload_validate(file: UploadFile) -> tuple[bytes, str]:
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
    return content, ext


@router.post("/services/bullet/{bullet_id}/carousel")
def upload_services_bullet_carousel_image(
    bullet_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> dict:
    content, _ext = _bullet_image_upload_validate(file)
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")

    cfg = get_app_config()
    storage_uri = upload_bytes(
        bucket=cfg.supabase_bucket_web_settings,
        content=content,
        filename=file.filename or "upload",
        folder=f"services/bullets/{bullet_id}",
        content_type=file.content_type,
    )
    prev = bullet.get("carouselImage")
    if prev and isinstance(prev, str) and is_supabase_uri(prev):
        delete_file_from_uri(prev)

    bullet["carouselImage"] = storage_uri
    bullet["carouselImageUrl"] = f"/api/customization/services/bullet/{bullet_id}/carousel-image"
    _persist_services(db, current, str(current_user.id))
    return {
        "carousel_image_url": bullet["carouselImageUrl"],
        "carousel_image": storage_uri,
    }


@router.delete("/services/bullet/{bullet_id}/carousel")
def delete_services_bullet_carousel_image(
    bullet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")

    prev = bullet.get("carouselImage")
    if prev and isinstance(prev, str) and is_supabase_uri(prev):
        delete_file_from_uri(prev)

    bullet.pop("carouselImage", None)
    bullet.pop("carouselImageUrl", None)
    _persist_services(db, current, str(current_user.id))


@router.get("/services/bullet/{bullet_id}/carousel-image")
def get_services_bullet_carousel_image(
    bullet_id: str,
    db: Session = Depends(get_db),
) -> Response:
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")
    uri = bullet.get("carouselImage")
    if not uri or not is_supabase_uri(str(uri)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No carousel image for this bullet.")

    uri_s = str(uri)
    raw = download_bytes_from_uri(uri_s)
    return Response(
        content=raw,
        media_type=_content_type_from_path(uri_s, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/services/bullet/{bullet_id}/icon")
def upload_services_bullet_icon_image(
    bullet_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> dict:
    content, _ext = _bullet_image_upload_validate(file)
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")

    cfg = get_app_config()
    storage_uri = upload_bytes(
        bucket=cfg.supabase_bucket_web_settings,
        content=content,
        filename=file.filename or "upload",
        folder=f"services/bullets/{bullet_id}/icons",
        content_type=file.content_type,
    )
    prev = bullet.get("bulletImage")
    if prev and isinstance(prev, str) and is_supabase_uri(prev):
        delete_file_from_uri(prev)

    bullet["bulletImage"] = storage_uri
    bullet["bulletImageUrl"] = f"/api/customization/services/bullet/{bullet_id}/icon-image"
    _persist_services(db, current, str(current_user.id))
    return {
        "bullet_image_url": bullet["bulletImageUrl"],
        "bullet_image": storage_uri,
    }


@router.delete("/services/bullet/{bullet_id}/icon")
def delete_services_bullet_icon_image(
    bullet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.editor)),
) -> None:
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")

    prev = bullet.get("bulletImage")
    if prev and isinstance(prev, str) and is_supabase_uri(prev):
        delete_file_from_uri(prev)

    bullet.pop("bulletImage", None)
    bullet.pop("bulletImageUrl", None)
    _persist_services(db, current, str(current_user.id))


@router.get("/services/bullet/{bullet_id}/icon-image")
def get_services_bullet_icon_image(bullet_id: str, db: Session = Depends(get_db)) -> Response:
    current = _services_row(db)
    _idx, bullet = _find_bullet(current, bullet_id)
    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found.")
    uri = bullet.get("bulletImage")
    if not uri or not is_supabase_uri(str(uri)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No bullet icon image.")

    uri_s = str(uri)
    raw = download_bytes_from_uri(uri_s)
    return Response(
        content=raw,
        media_type=_content_type_from_path(uri_s, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


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

    # Delete the previously stored file before replacing the reference.
    old_uri = current.get("previewImage")
    if old_uri and is_supabase_uri(old_uri):
        delete_file_from_uri(old_uri)

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
