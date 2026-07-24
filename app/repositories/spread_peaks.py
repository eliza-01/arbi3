from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exchange import Exchange
from app.db.models.spread_peak import SpreadPeak


class SpreadPeakRepository:
    async def upsert_all_time(self, session: AsyncSession, rows: list[dict]) -> None:
        if not rows:
            return
        statement = insert(SpreadPeak).values(rows)
        statement = statement.on_duplicate_key_update(
            all_time_at=func.if_(
                or_(
                    SpreadPeak.all_time_delta_pct.is_(None),
                    statement.inserted.all_time_delta_pct > SpreadPeak.all_time_delta_pct,
                ),
                statement.inserted.all_time_at,
                SpreadPeak.all_time_at,
            ),
            all_time_delta_pct=func.greatest(
                func.coalesce(SpreadPeak.all_time_delta_pct, statement.inserted.all_time_delta_pct),
                statement.inserted.all_time_delta_pct,
            ),
            updated_at=statement.inserted.updated_at,
        )
        await session.execute(statement)

    async def clear_window(self, session: AsyncSession, window: str) -> None:
        if window == "hour":
            await session.execute(
                update(SpreadPeak).values(hour_delta_pct=None, hour_at=None)
            )
        else:
            await session.execute(
                update(SpreadPeak).values(day_delta_pct=None, day_at=None)
            )

    async def update_window(
        self,
        session: AsyncSession,
        rows: list[tuple[int, int, int, Decimal, datetime]],
        window: str,
    ) -> None:
        now = datetime.now(UTC)
        values = []
        for asset_id, buy_exchange_id, sell_exchange_id, delta, observed_at in rows:
            item = {
                "asset_id": asset_id,
                "buy_exchange_id": buy_exchange_id,
                "sell_exchange_id": sell_exchange_id,
                "updated_at": now,
            }
            if window == "hour":
                item.update(hour_delta_pct=delta, hour_at=observed_at)
            else:
                item.update(day_delta_pct=delta, day_at=observed_at)
            values.append(item)
        if not values:
            return
        statement = insert(SpreadPeak).values(values)
        if window == "hour":
            statement = statement.on_duplicate_key_update(
                hour_delta_pct=statement.inserted.hour_delta_pct,
                hour_at=statement.inserted.hour_at,
                updated_at=statement.inserted.updated_at,
            )
        else:
            statement = statement.on_duplicate_key_update(
                day_delta_pct=statement.inserted.day_delta_pct,
                day_at=statement.inserted.day_at,
                updated_at=statement.inserted.updated_at,
            )
        await session.execute(statement)

    async def list_best_by_asset(self, session: AsyncSession) -> dict[int, dict]:
        statement = select(SpreadPeak)
        peaks = list((await session.scalars(statement)).all())
        exchange_codes = {
            exchange.id: exchange.code
            for exchange in (await session.scalars(select(Exchange))).all()
        }
        best: dict[int, dict] = {}
        for peak in peaks:
            current = best.setdefault(
                peak.asset_id,
                {
                    "all_time_pct": None,
                    "day_pct": None,
                    "hour_pct": None,
                    "buy_exchange": None,
                    "sell_exchange": None,
                },
            )
            if peak.all_time_delta_pct is not None and (
                current["all_time_pct"] is None
                or float(peak.all_time_delta_pct) > current["all_time_pct"]
            ):
                current["all_time_pct"] = float(peak.all_time_delta_pct)
                current["buy_exchange"] = exchange_codes.get(peak.buy_exchange_id)
                current["sell_exchange"] = exchange_codes.get(peak.sell_exchange_id)
            if peak.day_delta_pct is not None and (
                current["day_pct"] is None or float(peak.day_delta_pct) > current["day_pct"]
            ):
                current["day_pct"] = float(peak.day_delta_pct)
            if peak.hour_delta_pct is not None and (
                current["hour_pct"] is None or float(peak.hour_delta_pct) > current["hour_pct"]
            ):
                current["hour_pct"] = float(peak.hour_delta_pct)
        return best
