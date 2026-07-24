from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CatalogAsset:
    id: int
    base_asset: str
    quote_asset: str
    contract_type: str
    symbols: dict[str, str]
    exchange_ids: dict[str, int]
