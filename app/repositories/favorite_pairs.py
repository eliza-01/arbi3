from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exchange import Exchange
from app.db.models.favorite_pair import FavoritePair


class FavoritePairRepository:
    async def list_keys(self, session: AsyncSession) -> set[tuple[int, str, str]]:
        exchange_a = Exchange.__table__.alias("exchange_a")
        exchange_b = Exchange.__table__.alias("exchange_b")
        statement = (
            select(
                FavoritePair.asset_id,
                exchange_a.c.code,
                exchange_b.c.code,
            )
            .join(exchange_a, exchange_a.c.id == FavoritePair.exchange_a_id)
            .join(exchange_b, exchange_b.c.id == FavoritePair.exchange_b_id)
        )
        result: set[tuple[int, str, str]] = set()
        for asset_id, code_a, code_b in (await session.execute(statement)).all():
            left, right = sorted((str(code_a), str(code_b)))
            result.add((int(asset_id), left, right))
        return result

    async def add(
        self,
        session: AsyncSession,
        *,
        asset_id: int,
        exchange_a_id: int,
        exchange_b_id: int,
    ) -> None:
        left_id, right_id = sorted((exchange_a_id, exchange_b_id))
        key = {
            "asset_id": asset_id,
            "exchange_a_id": left_id,
            "exchange_b_id": right_id,
        }
        if await session.get(FavoritePair, key) is None:
            session.add(FavoritePair(**key, created_at=datetime.now(UTC)))

    async def remove(
        self,
        session: AsyncSession,
        *,
        asset_id: int,
        exchange_a_id: int,
        exchange_b_id: int,
    ) -> None:
        left_id, right_id = sorted((exchange_a_id, exchange_b_id))
        await session.execute(
            delete(FavoritePair).where(
                FavoritePair.asset_id == asset_id,
                FavoritePair.exchange_a_id == left_id,
                FavoritePair.exchange_b_id == right_id,
            )
        )

    async def remove_asset(self, session: AsyncSession, asset_id: int) -> None:
        await session.execute(delete(FavoritePair).where(FavoritePair.asset_id == asset_id))

    async def contains(
        self,
        session: AsyncSession,
        *,
        asset_id: int,
        exchange_a_id: int,
        exchange_b_id: int,
    ) -> bool:
        left_id, right_id = sorted((exchange_a_id, exchange_b_id))
        return (
            await session.scalar(
                select(FavoritePair.asset_id).where(
                    FavoritePair.asset_id == asset_id,
                    FavoritePair.exchange_a_id == left_id,
                    FavoritePair.exchange_b_id == right_id,
                )
            )
            is not None
        )
