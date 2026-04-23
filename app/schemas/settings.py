from typing import Any

from pydantic import BaseModel


class SiteSettingsResponse(BaseModel):
    data: Any | None = None


class UpsertSiteSettingsRequest(BaseModel):
    data: Any


class FaviconUploadResponse(BaseModel):
    favicon_url: str


class LogoUploadResponse(BaseModel):
    logo_url: str

