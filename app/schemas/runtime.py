from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.enums import CollectionMode


class RuntimeSettingsResponse(BaseModel):
    mode: CollectionMode
    interval_ms: int
    favorites_count: int


class RuntimeModeUpdate(BaseModel):
    mode: CollectionMode


class RuntimeIntervalUpdate(BaseModel):
    interval_ms: int = Field(
        ge=settings.min_quote_interval_ms,
        le=settings.max_quote_interval_ms,
    )
