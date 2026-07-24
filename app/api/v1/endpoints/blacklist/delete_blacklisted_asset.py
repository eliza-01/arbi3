from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container
from app.db.session import SessionFactory


async def delete_blacklisted_asset(
    asset_id: int,
    container: Container = Depends(get_container),
) -> dict:
    async with SessionFactory() as session:
        await container.blacklisted_asset_repository.remove(session, asset_id)
        await session.commit()
        blacklist_ids = await container.blacklisted_asset_repository.list_ids(session)

    await container.runtime.set_blacklist(blacklist_ids)
    return {"asset_id": asset_id, "is_blacklisted": False}
