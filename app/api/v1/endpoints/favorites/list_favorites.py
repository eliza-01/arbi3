from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def list_favorites(container: Container = Depends(get_container)) -> list[dict]:
    return await container.asset_read.execute(favorites_only=True)
