import asyncio
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from typing import Any

from app.db.session import SessionFactory
from app.exchanges.trading.errors import ExchangeRequestError
from app.exchanges.trading.models import ClosePositionRequest, OpenPositionRequest, OrderResult
from app.local_settings.store import LocalSettingsStore
from app.repositories.arbitrage_trades import ArbitrageTradeRepository
from app.services.arbitrage.insurance import position_quantity, wait_for_both_legs
from app.services.arbitrage.serialization import serialize_trade
from app.services.instruments.catalog import InstrumentCatalog
from app.services.quotes.store import QuoteStore
from app.services.spreads.calculator import calculate_directional_spreads
from app.services.spreads.pairs import normalize_exchange_pair, select_best_by_exchange_pair
from app.services.trading.adapter_registry import TradingAdapterRegistry


class OpenArbitragePairService:
    def __init__(
        self,
        *,
        catalog: InstrumentCatalog,
        quote_store: QuoteStore,
        settings_store: LocalSettingsStore,
        adapters: TradingAdapterRegistry,
        repository: ArbitrageTradeRepository,
        lock: asyncio.Lock | None = None,
    ) -> None:
        self._catalog = catalog
        self._quote_store = quote_store
        self._settings_store = settings_store
        self._adapters = adapters
        self._repository = repository
        self._lock = lock or asyncio.Lock()

    async def execute(
        self,
        *,
        asset_id: int,
        exchange_a: str,
        exchange_b: str,
    ) -> dict:
        async with self._lock:
            return await self._execute_locked(
                asset_id=asset_id,
                exchange_a=exchange_a,
                exchange_b=exchange_b,
            )

    async def _execute_locked(
        self,
        *,
        asset_id: int,
        exchange_a: str,
        exchange_b: str,
    ) -> dict:
        try:
            pair = normalize_exchange_pair(exchange_a.lower(), exchange_b.lower())
        except ValueError as exc:
            raise ExchangeRequestError(str(exc)) from exc
        asset = self._catalog.get(asset_id)
        if asset is None:
            raise ExchangeRequestError("Актив не найден")
        if pair[0] not in asset.symbols or pair[1] not in asset.symbols:
            raise ExchangeRequestError("Актив недоступен на выбранной паре бирж")

        spread = await self._current_pair_spread(asset, pair)
        settings = self._settings_store.load().trading
        buy_code = spread.buy_exchange
        sell_code = spread.sell_exchange
        buy_symbol = asset.symbols[buy_code]
        sell_symbol = asset.symbols[sell_code]
        exchange_a_id, exchange_b_id = sorted(
            (asset.exchange_ids[pair[0]], asset.exchange_ids[pair[1]])
        )

        async with SessionFactory() as session:
            existing = await self._repository.find_active_pair(
                session,
                asset_id=asset.id,
                exchange_a_id=exchange_a_id,
                exchange_b_id=exchange_b_id,
            )
            if existing is not None:
                raise ExchangeRequestError("По этой связке уже есть активная сделка")
            trade = await self._repository.create_opening(
                session,
                asset_id=asset.id,
                exchange_a_id=exchange_a_id,
                exchange_b_id=exchange_b_id,
                buy_exchange_id=asset.exchange_ids[buy_code],
                sell_exchange_id=asset.exchange_ids[sell_code],
                buy_symbol=buy_symbol,
                sell_symbol=sell_symbol,
                position_usdt=settings.position_usdt,
                leverage=settings.leverage,
                rounding=settings.rounding,
                insurance_seconds=settings.insurance_seconds,
                buy_quantity=None,
                sell_quantity=None,
                buy_order_id=None,
                sell_order_id=None,
                error_message=None,
                opened_at=None,
                closed_at=None,
            )
            await session.commit()
            trade_id = trade.id

        deadline = time.monotonic() + settings.insurance_seconds
        buy_result: OrderResult | None = None
        sell_result: OrderResult | None = None
        buy_quantity = 0.0
        sell_quantity = 0.0
        try:
            async with AsyncExitStack() as stack:
                buy_adapter = await stack.enter_async_context(self._adapters.create(buy_code))
                sell_adapter = await stack.enter_async_context(self._adapters.create(sell_code))

                buy_existing, sell_existing = await asyncio.gather(
                    buy_adapter.positions(buy_symbol),
                    sell_adapter.positions(sell_symbol),
                )
                if buy_existing:
                    raise ExchangeRequestError(
                        f"На {buy_code.upper()} уже есть позиция по {buy_symbol}"
                    )
                if sell_existing:
                    raise ExchangeRequestError(
                        f"На {sell_code.upper()} уже есть позиция по {sell_symbol}"
                    )

                remaining = max(deadline - time.monotonic(), 0.01)
                open_results = await asyncio.wait_for(
                    asyncio.gather(
                        buy_adapter.open_position(
                            OpenPositionRequest(
                                symbol=buy_symbol,
                                direction="long",
                                amount_usdt=settings.position_usdt,
                                leverage=settings.leverage,
                                rounding=settings.rounding,
                            )
                        ),
                        sell_adapter.open_position(
                            OpenPositionRequest(
                                symbol=sell_symbol,
                                direction="short",
                                amount_usdt=settings.position_usdt,
                                leverage=settings.leverage,
                                rounding=settings.rounding,
                            )
                        ),
                        return_exceptions=True,
                    ),
                    timeout=remaining,
                )
                open_errors = [
                    result for result in open_results if isinstance(result, Exception)
                ]
                if open_errors:
                    raise ExchangeRequestError(
                        "Не удалось открыть обе ноги: "
                        + " | ".join(str(error) for error in open_errors)
                    )
                buy_result, sell_result = open_results
                expected_buy = _expected_quantity(buy_result)
                expected_sell = _expected_quantity(sell_result)
                buy_quantity, sell_quantity = await wait_for_both_legs(
                    buy_adapter=buy_adapter,
                    sell_adapter=sell_adapter,
                    buy_symbol=buy_symbol,
                    sell_symbol=sell_symbol,
                    expected_buy=expected_buy,
                    expected_sell=expected_sell,
                    deadline=deadline,
                )
                if buy_quantity <= 0 or sell_quantity <= 0:
                    raise TimeoutError(
                        f"Обе ноги не подтверждены за {settings.insurance_seconds:g} сек"
                    )
        except Exception as exc:
            compensation_errors, remaining_buy, remaining_sell = await self._compensate(
                buy_code=buy_code,
                sell_code=sell_code,
                buy_symbol=buy_symbol,
                sell_symbol=sell_symbol,
                buy_quantity=buy_quantity,
                sell_quantity=sell_quantity,
                rounding=settings.rounding,
            )
            message = str(exc)
            if compensation_errors:
                message += " · Ошибка страховочного закрытия: " + " | ".join(compensation_errors)
            async with SessionFactory() as session:
                failed = await self._repository.get(session, trade_id)
                if failed is not None:
                    if remaining_buy > 0 or remaining_sell > 0:
                        self._repository.mark_open(
                            failed,
                            buy_quantity=remaining_buy,
                            sell_quantity=remaining_sell,
                            buy_order_id=buy_result.order_id if buy_result else None,
                            sell_order_id=sell_result.order_id if sell_result else None,
                        )
                        self._repository.mark_open_with_error(failed, message)
                    else:
                        self._repository.mark_failed(failed, message)
                    await session.commit()
            raise ExchangeRequestError(message) from exc

        async with SessionFactory() as session:
            opened = await self._repository.get(session, trade_id)
            if opened is None:
                raise ExchangeRequestError("Запись арбитражной сделки потеряна")
            self._repository.mark_open(
                opened,
                buy_quantity=buy_quantity,
                sell_quantity=sell_quantity,
                buy_order_id=buy_result.order_id if buy_result else None,
                sell_order_id=sell_result.order_id if sell_result else None,
            )
            await session.commit()
            return serialize_trade(opened, self._catalog)

    async def _current_pair_spread(self, asset, pair: tuple[str, str]):
        snapshot = await self._quote_store.snapshot()
        quotes = snapshot.get(asset.id, {})
        pair_quotes = {code: quotes[code] for code in pair if code in quotes}
        if len(pair_quotes) != 2:
            raise ExchangeRequestError("Нет свежих котировок для обеих бирж")
        now = datetime.now(UTC)
        stale = [
            code
            for code, quote in pair_quotes.items()
            if (now - quote.observed_at).total_seconds() > 30
        ]
        if stale:
            raise ExchangeRequestError(
                "Котировки устарели: " + ", ".join(code.upper() for code in stale)
            )
        pair_spreads = select_best_by_exchange_pair(
            calculate_directional_spreads(asset, pair_quotes)
        )
        spread = pair_spreads.get(pair)
        if spread is None:
            raise ExchangeRequestError("Не удалось рассчитать исполнимую ask→bid связку")
        return spread

    async def _compensate(
        self,
        *,
        buy_code: str,
        sell_code: str,
        buy_symbol: str,
        sell_symbol: str,
        buy_quantity: float,
        sell_quantity: float,
        rounding: str,
    ) -> tuple[list[str], float, float]:
        errors: list[str] = []
        async with AsyncExitStack() as stack:
            buy_adapter = await stack.enter_async_context(self._adapters.create(buy_code))
            sell_adapter = await stack.enter_async_context(self._adapters.create(sell_code))
            # Re-read positions because an HTTP timeout can happen after the exchange
            # has already accepted the market order.
            try:
                buy_quantity = max(
                    buy_quantity,
                    position_quantity(await buy_adapter.positions(buy_symbol), "long"),
                )
            except Exception as exc:
                errors.append(f"{buy_code.upper()} проверка: {exc}")
            try:
                sell_quantity = max(
                    sell_quantity,
                    position_quantity(await sell_adapter.positions(sell_symbol), "short"),
                )
            except Exception as exc:
                errors.append(f"{sell_code.upper()} проверка: {exc}")

            tasks: list[tuple[str, Any]] = []
            if buy_quantity > 0:
                tasks.append(
                    (
                        buy_code,
                        buy_adapter.close_position(
                            ClosePositionRequest(
                                symbol=buy_symbol,
                                direction="long",
                                quantity=buy_quantity,
                                rounding=rounding,
                            )
                        ),
                    )
                )
            if sell_quantity > 0:
                tasks.append(
                    (
                        sell_code,
                        sell_adapter.close_position(
                            ClosePositionRequest(
                                symbol=sell_symbol,
                                direction="short",
                                quantity=sell_quantity,
                                rounding=rounding,
                            )
                        ),
                    )
                )
            if tasks:
                results = await asyncio.gather(
                    *(task for _, task in tasks), return_exceptions=True
                )
                for (code, _), result in zip(tasks, results, strict=True):
                    if isinstance(result, Exception):
                        errors.append(f"{code.upper()} закрытие: {result}")
            # Bybit acknowledges order creation asynchronously. Give both
            # compensation orders a short confirmation window before deciding
            # that a leg is still exposed.
            final_buy, final_sell = buy_quantity, sell_quantity
            verify_deadline = time.monotonic() + 2.0
            while time.monotonic() < verify_deadline:
                try:
                    final_buy = position_quantity(await buy_adapter.positions(buy_symbol), "long")
                except Exception as exc:
                    errors.append(f"{buy_code.upper()} финальная проверка: {exc}")
                    break
                try:
                    final_sell = position_quantity(await sell_adapter.positions(sell_symbol), "short")
                except Exception as exc:
                    errors.append(f"{sell_code.upper()} финальная проверка: {exc}")
                    break
                if final_buy <= 0 and final_sell <= 0:
                    break
                await asyncio.sleep(0.2)
            if final_buy > 0:
                errors.append(f"{buy_code.upper()} осталась LONG {final_buy:g}")
            if final_sell > 0:
                errors.append(f"{sell_code.upper()} осталась SHORT {final_sell:g}")
        return errors, final_buy, final_sell


def _expected_quantity(result: OrderResult) -> float:
    calculation = result.raw.get("calculation") if isinstance(result.raw, dict) else None
    if not isinstance(calculation, dict):
        return 0.0
    try:
        return float(calculation.get("quantity") or 0)
    except (TypeError, ValueError):
        return 0.0
