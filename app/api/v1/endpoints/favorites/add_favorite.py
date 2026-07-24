from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_container
from app.container import Container
from app.db.session import SessionFactory


async def add_favorite(
    asset_id: int,
    container: Container = Depends(get_container),
) -> dict:
    if container.catalog.get(asset_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    async with SessionFactory() as session:
        await container.favorite_repository.add(session, asset_id)
        await session.commit()
        favorite_ids = await container.favorite_repository.list_ids(session)
    await container.runtime.set_favorites(favorite_ids)
    return {"asset_id": asset_id, "is_favorite": True}
