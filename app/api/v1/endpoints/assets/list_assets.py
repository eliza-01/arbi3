from fastapi import Depends, Query

from app.api.dependencies import get_container
from app.container import Container


async def list_assets(
    favorites_only: bool = Query(False),
    container: Container = Depends(get_container),
) -> list[dict]:
    return await container.asset_read.execute(favorites_only=favorites_only)
