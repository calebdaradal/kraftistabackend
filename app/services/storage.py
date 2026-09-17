from __future__ import annotations

import base64
import io
import mimetypes
import uuid
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from PIL import Image

from app.core.config import get_settings

B2_URI_PREFIX = "b2://"
IMAGE_SIZE = (512, 512)
IMAGE_QUALITY = 85


@lru_cache
def get_storage_client():
    settings = get_settings()
    if not settings.b2_key_id or not settings.b2_application_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Blackblaze B2 storage is not configured on backend.",
        )
    return boto3.client(
        "s3",
        endpoint_url=settings.b2_endpoint,
        aws_access_key_id=settings.b2_key_id,
        aws_secret_access_key=settings.b2_application_key,
        config=Config(signature_version="s3v4"),
    )


def is_data_url(value: str | None) -> bool:
    return bool(value and value.startswith("data:") and ";base64," in value)


def is_b2_uri(value: str | None) -> bool:
    return bool(value and value.startswith(B2_URI_PREFIX))


def parse_b2_uri(uri: str) -> str:
    """Extract object key from B2 URI (b2://object-key)."""
    return uri[len(B2_URI_PREFIX):]


def build_b2_uri(object_key: str) -> str:
    """Build B2 URI from object key."""
    return f"{B2_URI_PREFIX}{object_key}"


def _process_image(image_data: bytes) -> tuple[bytes, str]:
    """Resize and compress image to 512x512 with quality 85."""
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize with high-quality resampling
        img.thumbnail(IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # Save as JPEG with compression
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
        return output.getvalue(), "image/jpeg"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image data or unsupported format."
        ) from exc


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    """Decode base64 data URL."""
    meta, encoded = data_url.split(",", 1)
    mime = meta.split(";", 1)[0].replace("data:", "") or "application/octet-stream"
    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid base64 image data."
        ) from exc
    return content, mime


def _safe_ext_for_mime(mime: str) -> str:
    """Get file extension for MIME type."""
    ext = mimetypes.guess_extension(mime) or ""
    if ext == ".jpe":
        ext = ".jpg"
    return ext


def upload_data_url(folder: str, data_url: str) -> str:
    """Upload image from base64 data URL with processing."""
    content, mime = _decode_data_url(data_url)
    
    # Process image if it's an image type
    if mime.startswith("image/"):
        content, mime = _process_image(content)
    
    ext = _safe_ext_for_mime(mime)
    object_key = f"{folder.rstrip('/')}/{uuid.uuid4().hex}{ext}"
    
    settings = get_settings()
    client = get_storage_client()
    
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=mime,
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to B2: {str(exc)}"
        ) from exc
    
    return build_b2_uri(object_key)


def upload_bytes(content: bytes, filename: str, folder: str, content_type: str | None = None) -> str:
    """Upload raw bytes with optional image processing."""
    # Determine MIME type
    mime = content_type
    if not mime:
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
    # Process image if it's an image type
    if mime.startswith("image/"):
        content, mime = _process_image(content)
    
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    if not ext:
        ext = _safe_ext_for_mime(mime)
    
    object_key = f"{folder.rstrip('/')}/{uuid.uuid4().hex}{ext}"
    
    settings = get_settings()
    client = get_storage_client()
    
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=mime,
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to B2: {str(exc)}"
        ) from exc
    
    return build_b2_uri(object_key)


def create_signed_url_from_uri(uri: str, expires_in: int | None = None) -> str:
    """Create presigned URL for B2 object."""
    object_key = parse_b2_uri(uri)
    settings = get_settings()
    expiry = expires_in or settings.b2_signed_url_exp_seconds
    client = get_storage_client()
    
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": object_key},
            ExpiresIn=expiry,
        )
        return url
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create signed URL: {str(exc)}"
        ) from exc


def download_bytes_from_uri(uri: str) -> bytes:
    """Download bytes from B2 object."""
    object_key = parse_b2_uri(uri)
    settings = get_settings()
    client = get_storage_client()
    
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=object_key)
        return response["Body"].read()
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {str(exc)}"
        ) from exc


def delete_file_from_uri(uri: str) -> None:
    """Best-effort deletion — does not raise if file is missing."""
    try:
        if not is_b2_uri(uri):
            return
        object_key = parse_b2_uri(uri)
        settings = get_settings()
        client = get_storage_client()
        client.delete_object(Bucket=settings.b2_bucket_name, Key=object_key)
    except Exception:
        pass
