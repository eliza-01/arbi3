from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def get_trading_settings(
    container: Container = Depends(get_container),
) -> dict:
    return container.get_trading_settings.execute()
