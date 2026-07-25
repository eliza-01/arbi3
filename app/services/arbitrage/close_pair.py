import asyncio
import time
from contextlib import AsyncExitStack

from app.db.session import SessionFactory
from app.exchanges.trading.errors import ExchangeRequestError
from app.exchanges.trading.models import ClosePositionRequest
from app.repositories.arbitrage_trades import ArbitrageTradeRepository
from app.services.arbitrage.insurance import position_quantity
from app.services.arbitrage.serialization import exchange_code_by_id, serialize_trade
from app.services.instruments.catalog import InstrumentCatalog
from app.services.trading.adapter_registry import TradingAdapterRegistry


class CloseArbitragePairService:
    def __init__(
        self,
        *,
        catalog: InstrumentCatalog,
        adapters: TradingAdapterRegistry,
        repository: ArbitrageTradeRepository,
        lock: asyncio.Lock | None = None,
    ) -> None:
        self._catalog = catalog
        self._adapters = adapters
        self._repository = repository
        self._lock = lock or asyncio.Lock()

    async def execute(self, trade_id: int) -> dict:
        async with self._lock:
            return await self._execute_locked(trade_id)

    async def _execute_locked(self, trade_id: int) -> dict:
        async with SessionFactory() as session:
            trade = await self._repository.get(session, trade_id)
            if trade is None:
                raise ExchangeRequestError("Арбитражная сделка не найдена")
            if trade.status not in {"opening", "open", "closing"}:
                raise ExchangeRequestError("Арбитражная сделка уже закрыта")
            asset = self._catalog.get(trade.asset_id)
            if asset is None:
                raise ExchangeRequestError("Актив сделки больше не найден")
            buy_code = exchange_code_by_id(asset, trade.buy_exchange_id)
            sell_code = exchange_code_by_id(asset, trade.sell_exchange_id)
            if "unknown" in {buy_code, sell_code}:
                raise ExchangeRequestError("Биржи сделки больше не найдены")
            buy_quantity = float(trade.buy_quantity or 0)
            sell_quantity = float(trade.sell_quantity or 0)
            buy_symbol = trade.buy_symbol
            sell_symbol = trade.sell_symbol
            rounding = trade.rounding
            insurance_seconds = max(float(trade.insurance_seconds), 5.0)
            self._repository.mark_closing(trade)
            await session.commit()

        errors: list[str] = []
        async with AsyncExitStack() as stack:
            buy_adapter = await stack.enter_async_context(self._adapters.create(buy_code))
            sell_adapter = await stack.enter_async_context(self._adapters.create(sell_code))
            buy_before, sell_before = await asyncio.gather(
                buy_adapter.positions(buy_symbol),
                sell_adapter.positions(sell_symbol),
            )
            current_buy = position_quantity(buy_before, "long")
            current_sell = position_quantity(sell_before, "short")
            close_buy = min(buy_quantity, current_buy) if buy_quantity > 0 else current_buy
            close_sell = min(sell_quantity, current_sell) if sell_quantity > 0 else current_sell

            tasks: list[tuple[str, object]] = []
            if close_buy > 0:
                tasks.append(
                    (
                        buy_code,
                        buy_adapter.close_position(
                            ClosePositionRequest(
                                symbol=buy_symbol,
                                direction="long",
                                quantity=close_buy,
                                rounding=rounding,
                            )
                        ),
                    )
                )
            if close_sell > 0:
                tasks.append(
                    (
                        sell_code,
                        sell_adapter.close_position(
                            ClosePositionRequest(
                                symbol=sell_symbol,
                                direction="short",
                                quantity=close_sell,
                                rounding=rounding,
                            )
                        ),
                    )
                )
            results = await asyncio.gather(
                *(task for _, task in tasks), return_exceptions=True
            ) if tasks else []
            for (code, _), result in zip(tasks, results, strict=True):
                if isinstance(result, Exception):
                    errors.append(f"{code.upper()}: {result}")

            deadline = time.monotonic() + min(max(insurance_seconds, 5.0), 30.0)
            closed = False
            while time.monotonic() < deadline and not errors:
                buy_after, sell_after = await asyncio.gather(
                    buy_adapter.positions(buy_symbol),
                    sell_adapter.positions(sell_symbol),
                )
                remaining_buy = position_quantity(buy_after, "long")
                remaining_sell = position_quantity(sell_after, "short")
                buy_done = remaining_buy <= max(current_buy - close_buy, 0) + 1e-12
                sell_done = remaining_sell <= max(current_sell - close_sell, 0) + 1e-12
                if buy_done and sell_done:
                    closed = True
                    break
                await asyncio.sleep(0.2)
            if not closed and not errors:
                errors.append("Биржи не подтвердили закрытие обеих ног в установленный срок")

        async with SessionFactory() as session:
            trade = await self._repository.get(session, trade_id)
            if trade is None:
                raise ExchangeRequestError("Запись арбитражной сделки потеряна")
            if errors:
                message = " · ".join(errors)
                self._repository.mark_open_with_error(trade, message)
                await session.commit()
                raise ExchangeRequestError(message)
            self._repository.mark_closed(trade)
            await session.commit()
            return serialize_trade(trade, self._catalog)
