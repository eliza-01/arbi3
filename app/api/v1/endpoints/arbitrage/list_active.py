from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def list_active_arbitrage_trades(
    container: Container = Depends(get_container),
) -> list[dict]:
    return await container.list_active_arbitrage_trades.execute()
