from __future__ import annotations

import base64
import mimetypes
import uuid
from functools import lru_cache

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import get_settings

SB_URI_PREFIX = "sb://"


@lru_cache
def get_storage_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage is not configured on backend.",
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def is_data_url(value: str | None) -> bool:
    return bool(value and value.startswith("data:") and ";base64," in value)


def is_supabase_uri(value: str | None) -> bool:
    return bool(value and value.startswith(SB_URI_PREFIX))


def parse_supabase_uri(uri: str) -> tuple[str, str]:
    raw = uri[len(SB_URI_PREFIX) :]
    if "/" not in raw:
        raise ValueError("Invalid supabase uri")
    bucket, path = raw.split("/", 1)
    return bucket, path


def build_supabase_uri(bucket: str, path: str) -> str:
    return f"{SB_URI_PREFIX}{bucket}/{path}"


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    meta, encoded = data_url.split(",", 1)
    mime = meta.split(";", 1)[0].replace("data:", "") or "application/octet-stream"
    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid base64 image data.") from exc
    return content, mime


def _safe_ext_for_mime(mime: str) -> str:
    ext = mimetypes.guess_extension(mime) or ""
    if ext == ".jpe":
        ext = ".jpg"
    return ext


def upload_data_url(bucket: str, data_url: str, folder: str) -> str:
    content, mime = _decode_data_url(data_url)
    ext = _safe_ext_for_mime(mime)
    object_path = f"{folder.rstrip('/')}/{uuid.uuid4().hex}{ext}"
    client = get_storage_client()
    client.storage.from_(bucket).upload(
        object_path,
        content,
        {"content-type": mime, "upsert": "false"},
    )
    return build_supabase_uri(bucket, object_path)


def upload_bytes(bucket: str, content: bytes, filename: str, folder: str, content_type: str | None = None) -> str:
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    if not ext and content_type:
        ext = _safe_ext_for_mime(content_type)
    object_path = f"{folder.rstrip('/')}/{uuid.uuid4().hex}{ext}"
    client = get_storage_client()
    options = {"upsert": "false"}
    if content_type:
        options["content-type"] = content_type
    client.storage.from_(bucket).upload(object_path, content, options)
    return build_supabase_uri(bucket, object_path)


def create_signed_url_from_uri(uri: str, expires_in: int | None = None) -> str:
    bucket, path = parse_supabase_uri(uri)
    settings = get_settings()
    expiry = expires_in or settings.supabase_signed_url_exp_seconds
    res = get_storage_client().storage.from_(bucket).create_signed_url(path, expiry)
    signed_path = res.get("signedURL") or res.get("signedUrl")
    if not signed_path:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create signed URL.")
    if signed_path.startswith("http://") or signed_path.startswith("https://"):
        return signed_path
    base = settings.supabase_url.rstrip("/")
    return f"{base}/storage/v1{signed_path if signed_path.startswith('/') else '/' + signed_path}"


def download_bytes_from_uri(uri: str) -> bytes:
    bucket, path = parse_supabase_uri(uri)
    return get_storage_client().storage.from_(bucket).download(path)

