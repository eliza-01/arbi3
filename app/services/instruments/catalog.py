from app.db.session import SessionFactory
from app.repositories.assets import AssetRepository
from app.services.instruments.contracts import CatalogAsset


class InstrumentCatalog:
    def __init__(self, assets: AssetRepository) -> None:
        self._assets = assets
        self._by_asset_id: dict[int, CatalogAsset] = {}
        self._reverse: dict[str, dict[str, int]] = {}

    async def reload(self) -> None:
        async with SessionFactory() as session:
            rows = await self._assets.load_catalog_rows(session)
        grouped: dict[int, dict] = {}
        reverse: dict[str, dict[str, int]] = {}
        for asset_id, base, quote, contract_type, exchange_id, exchange_code, symbol in rows:
            item = grouped.setdefault(
                asset_id,
                {
                    "id": asset_id,
                    "base_asset": base,
                    "quote_asset": quote,
                    "contract_type": contract_type,
                    "symbols": {},
                    "exchange_ids": {},
                },
            )
            item["symbols"][exchange_code] = symbol
            item["exchange_ids"][exchange_code] = exchange_id
            reverse.setdefault(exchange_code, {})[symbol] = asset_id
        self._by_asset_id = {
            asset_id: CatalogAsset(**item) for asset_id, item in grouped.items()
        }
        self._reverse = reverse

    def all(self) -> list[CatalogAsset]:
        return list(self._by_asset_id.values())

    def get(self, asset_id: int) -> CatalogAsset | None:
        return self._by_asset_id.get(asset_id)

    def asset_id_for(self, exchange_code: str, symbol: str) -> int | None:
        return self._reverse.get(exchange_code, {}).get(symbol)

    def symbols_for(self, exchange_code: str, asset_ids: set[int] | None = None) -> set[str]:
        result = set()
        for asset in self._by_asset_id.values():
            if asset_ids is not None and asset.id not in asset_ids:
                continue
            symbol = asset.symbols.get(exchange_code)
            if symbol:
                result.add(symbol)
        return result
