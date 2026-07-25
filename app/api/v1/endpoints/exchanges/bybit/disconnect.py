from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container


async def disconnect_bybit(container: Container = Depends(get_container)) -> dict:
    return container.disconnect_bybit.execute()
