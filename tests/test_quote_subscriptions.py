from app.core.enums import CollectionMode
from app.services.quotes.subscriptions import (
    is_pair_active,
    select_active_asset_ids,
    select_active_asset_ids_for_exchange,
)
from app.services.runtime.state import RuntimeSnapshot


def make_snapshot(
    mode: CollectionMode,
    favorites: set[tuple[int, str, str]],
    blacklist: set[int],
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        mode=mode,
        interval_ms=1000,
        favorite_pairs=favorites,
        blacklist_ids=blacklist,
    )


def test_blacklist_is_excluded_in_all_mode() -> None:
    active = select_active_asset_ids(
        {1, 2, 3},
        make_snapshot(CollectionMode.ALL, {(1, "binance", "bybit")}, {2}),
    )
    assert active == {1, 3}


def test_blacklist_is_excluded_in_favorites_mode() -> None:
    active = select_active_asset_ids(
        {1, 2, 3},
        make_snapshot(
            CollectionMode.FAVORITES,
            {(1, "binance", "bybit"), (2, "binance", "bybit")},
            {2},
        ),
    )
    assert active == {1}


def test_favorites_mode_subscribes_only_pair_exchanges() -> None:
    snapshot = make_snapshot(
        CollectionMode.FAVORITES,
        {(1, "binance", "bybit"), (2, "bybit", "mexc")},
        set(),
    )
    assert select_active_asset_ids_for_exchange({1, 2}, "binance", snapshot) == {1}
    assert select_active_asset_ids_for_exchange({1, 2}, "bybit", snapshot) == {1, 2}
    assert select_active_asset_ids_for_exchange({1, 2}, "mexc", snapshot) == {2}


def test_pair_identity_is_not_directional() -> None:
    snapshot = make_snapshot(
        CollectionMode.FAVORITES,
        {(1, "binance", "bybit")},
        set(),
    )
    assert is_pair_active(1, "binance", "bybit", snapshot)
    assert is_pair_active(1, "bybit", "binance", snapshot)
