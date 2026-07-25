from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def get_binance_status(
    container: Container = Depends(get_container),
) -> dict:
    return await container.get_binance_status.execute()
