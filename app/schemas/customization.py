from typing import Any

from pydantic import BaseModel


class SiteCustomizationResponse(BaseModel):
    about: Any | None = None
    footer: Any | None = None
    hero: Any | None = None
    services: Any | None = None


class UpsertCustomizationRequest(BaseModel):
    data: Any

