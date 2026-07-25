import asyncio

from app.db.session import SessionFactory, engine
from app.exchanges.registry import ExchangeRegistry
from app.local_settings.store import LocalSettingsStore
from app.services.exchange_accounts.binance_adapter_factory import BinanceTradingAdapterFactory
from app.services.exchange_accounts.connect_binance import ConnectBinanceService
from app.services.exchange_accounts.disconnect_binance import DisconnectBinanceService
from app.services.exchange_accounts.get_binance_balance import GetBinanceBalanceService
from app.services.exchange_accounts.get_binance_settings import GetBinanceSettingsService
from app.services.exchange_accounts.get_binance_status import GetBinanceStatusService
from app.services.trading.close_binance_position import CloseBinancePositionService
from app.services.trading.get_settings import GetTradingSettingsService
from app.services.trading.list_binance_positions import ListBinancePositionsService
from app.services.trading.open_binance_position import OpenBinancePositionService
from app.services.trading.preview_volume import PreviewBinanceVolumeService
from app.services.trading.set_binance_leverage import SetBinanceLeverageService
from app.services.trading.update_settings import UpdateTradingSettingsService
from app.repositories.assets import AssetRepository
from app.repositories.blacklisted_assets import BlacklistedAssetRepository
from app.repositories.exchanges import ExchangeRepository
from app.repositories.favorites import FavoriteRepository
from app.repositories.spread_buckets import SpreadBucketRepository
from app.repositories.spread_peaks import SpreadPeakRepository
from app.services.assets.read import AssetReadService
from app.services.blacklist.read import BlacklistReadService
from app.services.broadcast.hub import BroadcastHub
from app.services.instruments.catalog import InstrumentCatalog
from app.services.instruments.sync import InstrumentSyncService
from app.services.quotes.store import QuoteStore
from app.services.quotes.supervisor import CollectorSupervisor
from app.services.runtime.state import RuntimeState
from app.services.spreads.accumulator import SpreadAccumulator
from app.services.spreads.engine import SpreadEngine
from app.services.spreads.persistence import SpreadPersistenceService
from app.services.spreads.window_refresh import SpreadWindowRefreshService


class Container:
    def __init__(self) -> None:
        self.exchange_registry = ExchangeRegistry()
        self.local_settings_store = LocalSettingsStore()
        self.binance_trading_adapter_factory = BinanceTradingAdapterFactory(
            self.local_settings_store,
        )
        self.get_binance_settings = GetBinanceSettingsService(self.local_settings_store)
        self.get_binance_status = GetBinanceStatusService(
            self.binance_trading_adapter_factory,
        )
        self.get_binance_balance = GetBinanceBalanceService(
            self.binance_trading_adapter_factory,
        )
        self.connect_binance = ConnectBinanceService(
            self.local_settings_store,
            self.binance_trading_adapter_factory,
        )
        self.disconnect_binance = DisconnectBinanceService(self.local_settings_store)
        self.get_trading_settings = GetTradingSettingsService(self.local_settings_store)
        self.update_trading_settings = UpdateTradingSettingsService(
            self.local_settings_store,
        )
        self.preview_binance_volume = PreviewBinanceVolumeService(
            self.binance_trading_adapter_factory,
        )
        self.list_binance_positions = ListBinancePositionsService(
            self.binance_trading_adapter_factory,
        )
        self.set_binance_leverage = SetBinanceLeverageService(
            self.binance_trading_adapter_factory,
        )
        self.open_binance_position = OpenBinancePositionService(
            self.local_settings_store,
            self.binance_trading_adapter_factory,
        )
        self.close_binance_position = CloseBinancePositionService(
            self.local_settings_store,
            self.binance_trading_adapter_factory,
        )
        self.exchange_repository = ExchangeRepository()
        self.asset_repository = AssetRepository()
        self.favorite_repository = FavoriteRepository()
        self.blacklisted_asset_repository = BlacklistedAssetRepository()
        self.spread_bucket_repository = SpreadBucketRepository()
        self.spread_peak_repository = SpreadPeakRepository()

        self.catalog = InstrumentCatalog(self.asset_repository)
        self.runtime = RuntimeState()
        self.quote_store = QuoteStore()
        self.hub = BroadcastHub()
        self.accumulator = SpreadAccumulator()

        self.instrument_sync = InstrumentSyncService(
            self.exchange_registry,
            self.exchange_repository,
            self.asset_repository,
            self.catalog,
        )
        self.asset_read = AssetReadService(
            self.asset_repository,
            self.favorite_repository,
            self.blacklisted_asset_repository,
            self.spread_peak_repository,
        )
        self.blacklist_read = BlacklistReadService(
            self.blacklisted_asset_repository,
        )
        self.collector_supervisor = CollectorSupervisor(
            self.exchange_registry,
            self.catalog,
            self.quote_store,
            self.runtime,
        )
        self.spread_engine = SpreadEngine(
            self.catalog,
            self.quote_store,
            self.runtime,
            self.accumulator,
            self.hub,
        )
        self.spread_persistence = SpreadPersistenceService(
            self.accumulator,
            self.spread_bucket_repository,
            self.spread_peak_repository,
        )
        self.window_refresh = SpreadWindowRefreshService(
            self.spread_bucket_repository,
            self.spread_peak_repository,
        )
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        await self.instrument_sync.execute()
        async with SessionFactory() as session:
            favorites = await self.favorite_repository.list_ids(session)
            blacklist = await self.blacklisted_asset_repository.list_ids(session)
        await self.runtime.set_favorites(favorites)
        await self.runtime.set_blacklist(blacklist)
        self.runtime.changed.clear()
        self._tasks = [
            asyncio.create_task(self.collector_supervisor.run(), name="collector-supervisor"),
            asyncio.create_task(self.spread_engine.run(), name="spread-engine"),
            asyncio.create_task(self.spread_persistence.run(), name="spread-persistence"),
            asyncio.create_task(self.window_refresh.run(), name="spread-window-refresh"),
        ]

    async def stop(self) -> None:
        self.collector_supervisor.stop()
        self.spread_engine.stop()
        self.spread_persistence.stop()
        self.window_refresh.stop()
        await self.spread_persistence.flush()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.exchange_registry.close()
        await engine.dispose()
