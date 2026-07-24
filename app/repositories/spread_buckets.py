from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.spread_bucket import SpreadBucket


class SpreadBucketRepository:
    async def upsert_many(self, session: AsyncSession, rows: list[dict]) -> None:
        if not rows:
            return
        statement = insert(SpreadBucket).values(rows)
        statement = statement.on_duplicate_key_update(
            max_delta_pct=func.greatest(
                SpreadBucket.max_delta_pct, statement.inserted.max_delta_pct
            ),
            max_delta_abs=func.if_(
                statement.inserted.max_delta_pct > SpreadBucket.max_delta_pct,
                statement.inserted.max_delta_abs,
                SpreadBucket.max_delta_abs,
            ),
            observed_at=func.if_(
                statement.inserted.max_delta_pct > SpreadBucket.max_delta_pct,
                statement.inserted.observed_at,
                SpreadBucket.observed_at,
            ),
        )
        await session.execute(statement)

    async def delete_older_than(self, session: AsyncSession, cutoff: datetime) -> None:
        await session.execute(delete(SpreadBucket).where(SpreadBucket.bucket_start < cutoff))

    async def window_maxima(
        self, session: AsyncSession, cutoff: datetime
    ) -> list[tuple[int, int, int, Decimal, datetime]]:
        max_subquery = (
            select(
                SpreadBucket.asset_id.label("asset_id"),
                SpreadBucket.buy_exchange_id.label("buy_exchange_id"),
                SpreadBucket.sell_exchange_id.label("sell_exchange_id"),
                func.max(SpreadBucket.max_delta_pct).label("max_delta_pct"),
            )
            .where(SpreadBucket.bucket_start >= cutoff)
            .group_by(
                SpreadBucket.asset_id,
                SpreadBucket.buy_exchange_id,
                SpreadBucket.sell_exchange_id,
            )
            .subquery()
        )
        statement = (
            select(
                SpreadBucket.asset_id,
                SpreadBucket.buy_exchange_id,
                SpreadBucket.sell_exchange_id,
                SpreadBucket.max_delta_pct,
                func.max(SpreadBucket.observed_at),
            )
            .join(
                max_subquery,
                (SpreadBucket.asset_id == max_subquery.c.asset_id)
                & (SpreadBucket.buy_exchange_id == max_subquery.c.buy_exchange_id)
                & (SpreadBucket.sell_exchange_id == max_subquery.c.sell_exchange_id)
                & (SpreadBucket.max_delta_pct == max_subquery.c.max_delta_pct),
            )
            .where(SpreadBucket.bucket_start >= cutoff)
            .group_by(
                SpreadBucket.asset_id,
                SpreadBucket.buy_exchange_id,
                SpreadBucket.sell_exchange_id,
                SpreadBucket.max_delta_pct,
            )
        )
        return list((await session.execute(statement)).all())
