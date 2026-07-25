import asyncio
from dataclasses import dataclass

from app.core.config import settings
from app.core.enums import CollectionMode

FavoritePairKey = tuple[int, str, str]


@dataclass(slots=True, frozen=True)
class RuntimeSnapshot:
    mode: CollectionMode
    interval_ms: int
    favorite_pairs: set[FavoritePairKey]
    blacklist_ids: set[int]

    @property
    def favorite_ids(self) -> set[int]:
        return {asset_id for asset_id, _, _ in self.favorite_pairs}


class RuntimeState:
    def __init__(self) -> None:
        self._mode = CollectionMode(settings.default_collection_mode)
        self._interval_ms = settings.default_quote_interval_ms
        self._favorite_pairs: set[FavoritePairKey] = set()
        self._blacklist_ids: set[int] = set()
        self._lock = asyncio.Lock()
        self.changed = asyncio.Event()

    async def snapshot(self) -> RuntimeSnapshot:
        async with self._lock:
            return RuntimeSnapshot(
                mode=self._mode,
                interval_ms=self._interval_ms,
                favorite_pairs=set(self._favorite_pairs),
                blacklist_ids=set(self._blacklist_ids),
            )

    async def set_mode(self, mode: CollectionMode) -> None:
        async with self._lock:
            self._mode = mode
        self.changed.set()

    async def set_interval(self, interval_ms: int) -> None:
        async with self._lock:
            self._interval_ms = interval_ms
        self.changed.set()

    async def set_favorites(self, favorite_pairs: set[FavoritePairKey]) -> None:
        async with self._lock:
            self._favorite_pairs = set(favorite_pairs)
        self.changed.set()

    async def set_blacklist(self, blacklist_ids: set[int]) -> None:
        async with self._lock:
            self._blacklist_ids = set(blacklist_ids)
        self.changed.set()
