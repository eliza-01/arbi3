from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_container
from app.container import Container
from app.db.session import SessionFactory


async def add_blacklisted_asset(
    asset_id: int,
    container: Container = Depends(get_container),
) -> dict:
    if container.catalog.get(asset_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    async with SessionFactory() as session:
        if await container.arbitrage_trade_repository.has_active_asset(session, asset_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Сначала закройте активную арбитражную связку",
            )
        await container.blacklisted_asset_repository.add(session, asset_id)
        await container.favorite_pair_repository.remove_asset(session, asset_id)
        await session.commit()
        favorite_pairs = await container.favorite_pair_repository.list_keys(session)
        blacklist_ids = await container.blacklisted_asset_repository.list_ids(session)

    await container.runtime.set_favorites(favorite_pairs)
    await container.runtime.set_blacklist(blacklist_ids)
    return {"asset_id": asset_id, "is_blacklisted": True}
