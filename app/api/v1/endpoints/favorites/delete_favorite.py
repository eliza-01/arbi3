from fastapi import Depends

from app.api.dependencies import get_container
from app.container import Container
from app.db.session import SessionFactory


async def delete_favorite(
    asset_id: int,
    container: Container = Depends(get_container),
) -> dict:
    async with SessionFactory() as session:
        await container.favorite_repository.remove(session, asset_id)
        await session.commit()
        favorite_ids = await container.favorite_repository.list_ids(session)
    await container.runtime.set_favorites(favorite_ids)
    return {"asset_id": asset_id, "is_favorite": False}
