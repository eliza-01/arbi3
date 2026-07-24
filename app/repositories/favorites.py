from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.favorite import Favorite


class FavoriteRepository:
    async def list_ids(self, session: AsyncSession) -> set[int]:
        result = await session.scalars(select(Favorite.asset_id))
        return set(result)

    async def add(self, session: AsyncSession, asset_id: int) -> None:
        favorite = await session.get(Favorite, asset_id)
        if favorite is None:
            session.add(Favorite(asset_id=asset_id, created_at=datetime.now(UTC)))

    async def remove(self, session: AsyncSession, asset_id: int) -> None:
        await session.execute(delete(Favorite).where(Favorite.asset_id == asset_id))
