from itertools import combinations

from app.db.session import SessionFactory
from app.repositories.blacklisted_assets import BlacklistedAssetRepository
from app.repositories.favorite_pairs import FavoritePairRepository
from app.repositories.spread_peaks import SpreadPeakRepository
from app.services.instruments.catalog import InstrumentCatalog
from app.services.spreads.pairs import pair_row_key

_EMPTY_PEAKS = {
    "all_time_pct": None,
    "all_time_min_pct": None,
    "day_pct": None,
    "day_min_pct": None,
    "hour_pct": None,
    "hour_min_pct": None,
}


class AssetReadService:
    def __init__(
        self,
        catalog: InstrumentCatalog,
        favorites: FavoritePairRepository,
        blacklist: BlacklistedAssetRepository,
        peaks: SpreadPeakRepository,
    ) -> None:
        self._catalog = catalog
        self._favorites = favorites
        self._blacklist = blacklist
        self._peaks = peaks

    async def execute(self, favorites_only: bool = False) -> list[dict]:
        async with SessionFactory() as session:
            favorite_keys = await self._favorites.list_keys(session)
            blacklist_ids = await self._blacklist.list_ids(session)
            peaks = await self._peaks.list_best_by_pair(session)

        result: list[dict] = []
        for asset in self._catalog.all():
            if asset.id in blacklist_ids:
                continue
            exchange_codes = sorted(asset.symbols)
            for exchange_a, exchange_b in combinations(exchange_codes, 2):
                favorite_key = (asset.id, exchange_a, exchange_b)
                is_favorite = favorite_key in favorite_keys
                if favorites_only and not is_favorite:
                    continue
                result.append(
                    {
                        "row_key": pair_row_key(asset.id, exchange_a, exchange_b),
                        "id": asset.id,
                        "asset_id": asset.id,
                        "base_asset": asset.base_asset,
                        "quote_asset": asset.quote_asset,
                        "contract_type": asset.contract_type,
                        "display_symbol": f"{asset.base_asset}/{asset.quote_asset}",
                        "exchange_a": exchange_a,
                        "exchange_b": exchange_b,
                        "exchange_pair": [exchange_a, exchange_b],
                        "is_favorite": is_favorite,
                        "peaks": peaks.get(favorite_key, dict(_EMPTY_PEAKS)),
                    }
                )
        return result
