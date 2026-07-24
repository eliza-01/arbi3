from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container
from app.schemas.runtime import RuntimeIntervalUpdate, RuntimeSettingsResponse


async def update_runtime_interval(
    payload: RuntimeIntervalUpdate,
    container: Container = Depends(get_container),
) -> RuntimeSettingsResponse:
    await container.runtime.set_interval(payload.interval_ms)
    snapshot = await container.runtime.snapshot()
    return RuntimeSettingsResponse(
        mode=snapshot.mode,
        interval_ms=snapshot.interval_ms,
        favorites_count=len(snapshot.favorite_ids),
    )
