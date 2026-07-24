from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def list_blacklisted_assets(
    container: Container = Depends(get_container),
) -> list[dict]:
    return await container.blacklist_read.execute()
