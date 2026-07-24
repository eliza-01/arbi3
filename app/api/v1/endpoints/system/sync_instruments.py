from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def sync_instruments(container: Container = Depends(get_container)) -> dict:
    counts = await container.instrument_sync.execute()
    container.collector_supervisor.request_restart()
    return {"synced": counts, "common_assets": len(container.catalog.all())}
