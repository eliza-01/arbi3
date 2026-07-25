from app.core.enums import CollectionMode
from app.services.runtime.state import RuntimeSnapshot


def select_active_asset_ids(
    all_asset_ids: set[int],
    runtime: RuntimeSnapshot,
) -> set[int]:
    selected_ids = (
        runtime.favorite_ids & all_asset_ids
        if runtime.mode == CollectionMode.FAVORITES
        else all_asset_ids
    )
    return set(selected_ids) - runtime.blacklist_ids


def select_active_asset_ids_for_exchange(
    all_asset_ids: set[int],
    exchange_code: str,
    runtime: RuntimeSnapshot,
) -> set[int]:
    if runtime.mode != CollectionMode.FAVORITES:
        return set(all_asset_ids) - runtime.blacklist_ids
    selected = {
        asset_id
        for asset_id, exchange_a, exchange_b in runtime.favorite_pairs
        if exchange_code in {exchange_a, exchange_b}
    }
    return (selected & all_asset_ids) - runtime.blacklist_ids


def is_pair_active(
    asset_id: int,
    exchange_a: str,
    exchange_b: str,
    runtime: RuntimeSnapshot,
) -> bool:
    if asset_id in runtime.blacklist_ids:
        return False
    if runtime.mode != CollectionMode.FAVORITES:
        return True
    normalized = tuple(sorted((exchange_a, exchange_b)))
    return (asset_id, normalized[0], normalized[1]) in runtime.favorite_pairs
