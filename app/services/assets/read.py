from app.db.session import SessionFactory
from app.repositories.assets import AssetRepository
from app.repositories.favorites import FavoriteRepository
from app.repositories.spread_peaks import SpreadPeakRepository


class AssetReadService:
    def __init__(
        self,
        assets: AssetRepository,
        favorites: FavoriteRepository,
        peaks: SpreadPeakRepository,
    ) -> None:
        self._assets = assets
        self._favorites = favorites
        self._peaks = peaks

    async def execute(self, favorites_only: bool = False) -> list[dict]:
        async with SessionFactory() as session:
            assets = await self._assets.list_comparable(session)
            favorite_ids = await self._favorites.list_ids(session)
            peaks = await self._peaks.list_best_by_asset(session)
        result = []
        for asset in assets:
            if favorites_only and asset.id not in favorite_ids:
                continue
            result.append(
                {
                    "id": asset.id,
                    "base_asset": asset.base_asset,
                    "quote_asset": asset.quote_asset,
                    "contract_type": asset.contract_type,
                    "display_symbol": f"{asset.base_asset}/{asset.quote_asset}",
                    "is_favorite": asset.id in favorite_ids,
                    "peaks": peaks.get(
                        asset.id,
                        {
                            "all_time_pct": None,
                            "all_time_min_pct": None,
                            "day_pct": None,
                            "day_min_pct": None,
                            "hour_pct": None,
                            "hour_min_pct": None,
                            "buy_exchange": None,
                            "sell_exchange": None,
                        },
                    ),
                }
            )
        return result
