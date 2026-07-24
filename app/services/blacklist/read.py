from app.db.session import SessionFactory
from app.repositories.blacklisted_assets import BlacklistedAssetRepository


class BlacklistReadService:
    def __init__(self, blacklist: BlacklistedAssetRepository) -> None:
        self._blacklist = blacklist

    async def execute(self) -> list[dict]:
        async with SessionFactory() as session:
            rows = await self._blacklist.list_assets(session)

        return [
            {
                "id": asset.id,
                "base_asset": asset.base_asset,
                "quote_asset": asset.quote_asset,
                "contract_type": asset.contract_type,
                "display_symbol": f"{asset.base_asset}/{asset.quote_asset}",
                "created_at": created_at.isoformat(),
            }
            for asset, created_at in rows
        ]
