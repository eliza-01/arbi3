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
