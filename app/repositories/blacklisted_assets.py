from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.asset import Asset
from app.db.models.blacklisted_asset import BlacklistedAsset


class BlacklistedAssetRepository:
    async def list_ids(self, session: AsyncSession) -> set[int]:
        result = await session.scalars(select(BlacklistedAsset.asset_id))
        return set(result)

    async def list_assets(self, session: AsyncSession) -> list[tuple[Asset, datetime]]:
        statement = (
            select(Asset, BlacklistedAsset.created_at)
            .join(BlacklistedAsset, BlacklistedAsset.asset_id == Asset.id)
            .order_by(Asset.base_asset, Asset.quote_asset)
        )
        return list((await session.execute(statement)).all())

    async def contains(self, session: AsyncSession, asset_id: int) -> bool:
        return await session.get(BlacklistedAsset, asset_id) is not None

    async def add(self, session: AsyncSession, asset_id: int) -> None:
        item = await session.get(BlacklistedAsset, asset_id)
        if item is None:
            session.add(
                BlacklistedAsset(asset_id=asset_id, created_at=datetime.now(UTC))
            )

    async def remove(self, session: AsyncSession, asset_id: int) -> None:
        await session.execute(
            delete(BlacklistedAsset).where(BlacklistedAsset.asset_id == asset_id)
        )
