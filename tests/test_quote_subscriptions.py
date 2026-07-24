from app.core.enums import CollectionMode
from app.services.quotes.subscriptions import select_active_asset_ids
from app.services.runtime.state import RuntimeSnapshot


def make_snapshot(
    mode: CollectionMode,
    favorites: set[int],
    blacklist: set[int],
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        mode=mode,
        interval_ms=1000,
        favorite_ids=favorites,
        blacklist_ids=blacklist,
    )


def test_blacklist_is_excluded_in_all_mode() -> None:
    active = select_active_asset_ids(
        {1, 2, 3},
        make_snapshot(CollectionMode.ALL, {1}, {2}),
    )

    assert active == {1, 3}


def test_blacklist_is_excluded_in_favorites_mode() -> None:
    active = select_active_asset_ids(
        {1, 2, 3},
        make_snapshot(CollectionMode.FAVORITES, {1, 2}, {2}),
    )

    assert active == {1}
