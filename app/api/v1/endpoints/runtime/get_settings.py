from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container
from app.schemas.runtime import RuntimeSettingsResponse


async def get_runtime_settings(
    container: Container = Depends(get_container),
) -> RuntimeSettingsResponse:
    snapshot = await container.runtime.snapshot()
    return RuntimeSettingsResponse(
        mode=snapshot.mode,
        interval_ms=snapshot.interval_ms,
        favorites_count=len(snapshot.favorite_ids),
    )
