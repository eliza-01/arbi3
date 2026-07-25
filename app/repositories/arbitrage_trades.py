from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.arbitrage_trade import ArbitrageTrade

ACTIVE_STATUSES = ("opening", "open", "closing")


class ArbitrageTradeRepository:
    async def list_active(self, session: AsyncSession) -> list[ArbitrageTrade]:
        result = await session.scalars(
            select(ArbitrageTrade)
            .where(ArbitrageTrade.status.in_(ACTIVE_STATUSES))
            .order_by(ArbitrageTrade.created_at.asc())
        )
        return list(result)

    async def get(self, session: AsyncSession, trade_id: int) -> ArbitrageTrade | None:
        return await session.get(ArbitrageTrade, trade_id)

    async def find_active_pair(
        self,
        session: AsyncSession,
        *,
        asset_id: int,
        exchange_a_id: int,
        exchange_b_id: int,
    ) -> ArbitrageTrade | None:
        left_id, right_id = sorted((exchange_a_id, exchange_b_id))
        return await session.scalar(
            select(ArbitrageTrade)
            .where(
                ArbitrageTrade.asset_id == asset_id,
                ArbitrageTrade.exchange_a_id == left_id,
                ArbitrageTrade.exchange_b_id == right_id,
                ArbitrageTrade.status.in_(ACTIVE_STATUSES),
            )
            .order_by(ArbitrageTrade.id.desc())
            .limit(1)
        )

    async def has_active_asset(self, session: AsyncSession, asset_id: int) -> bool:
        return (
            await session.scalar(
                select(ArbitrageTrade.id)
                .where(
                    ArbitrageTrade.asset_id == asset_id,
                    ArbitrageTrade.status.in_(ACTIVE_STATUSES),
                )
                .limit(1)
            )
            is not None
        )

    async def create_opening(self, session: AsyncSession, **values) -> ArbitrageTrade:
        now = datetime.now(UTC)
        trade = ArbitrageTrade(
            **values,
            status="opening",
            created_at=now,
            updated_at=now,
        )
        session.add(trade)
        await session.flush()
        return trade

    def mark_open(
        self,
        trade: ArbitrageTrade,
        *,
        buy_quantity: float,
        sell_quantity: float,
        buy_order_id: str | None,
        sell_order_id: str | None,
    ) -> None:
        now = datetime.now(UTC)
        trade.status = "open"
        trade.buy_quantity = Decimal(str(buy_quantity))
        trade.sell_quantity = Decimal(str(sell_quantity))
        trade.buy_order_id = buy_order_id
        trade.sell_order_id = sell_order_id
        trade.error_message = None
        trade.opened_at = now
        trade.updated_at = now

    def mark_closing(self, trade: ArbitrageTrade) -> None:
        trade.status = "closing"
        trade.error_message = None
        trade.updated_at = datetime.now(UTC)

    def mark_closed(self, trade: ArbitrageTrade) -> None:
        now = datetime.now(UTC)
        trade.status = "closed"
        trade.error_message = None
        trade.closed_at = now
        trade.updated_at = now

    def mark_failed(self, trade: ArbitrageTrade, message: str) -> None:
        trade.status = "failed"
        trade.error_message = message[:4000]
        trade.closed_at = datetime.now(UTC)
        trade.updated_at = trade.closed_at

    def mark_open_with_error(self, trade: ArbitrageTrade, message: str) -> None:
        trade.status = "open"
        trade.error_message = message[:4000]
        trade.updated_at = datetime.now(UTC)
