from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def disconnect_binance(
    container: Container = Depends(get_container),
) -> dict:
    return container.disconnect_binance.execute()
