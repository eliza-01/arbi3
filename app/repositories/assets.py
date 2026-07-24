from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.asset import Asset
from app.db.models.exchange import Exchange
from app.db.models.exchange_symbol import ExchangeSymbol
from app.exchanges.contracts import InstrumentDescriptor


class AssetRepository:
    async def mark_exchange_symbols_inactive(self, session: AsyncSession, exchange_id: int) -> None:
        await session.execute(
            update(ExchangeSymbol)
            .where(ExchangeSymbol.exchange_id == exchange_id)
            .values(active=False)
        )

    async def upsert_instrument(
        self,
        session: AsyncSession,
        exchange_id: int,
        instrument: InstrumentDescriptor,
    ) -> None:
        now = datetime.now(UTC)
        asset = await session.scalar(
            select(Asset).where(
                Asset.base_asset == instrument.base_asset,
                Asset.quote_asset == instrument.quote_asset,
                Asset.contract_type == instrument.contract_type,
            )
        )
        if asset is None:
            asset = Asset(
                base_asset=instrument.base_asset,
                quote_asset=instrument.quote_asset,
                contract_type=instrument.contract_type,
                comparable=False,
                created_at=now,
                updated_at=now,
            )
            session.add(asset)
            await session.flush()
        else:
            asset.updated_at = now

        exchange_symbol = await session.scalar(
            select(ExchangeSymbol).where(
                ExchangeSymbol.exchange_id == exchange_id,
                ExchangeSymbol.symbol == instrument.symbol,
            )
        )
        if exchange_symbol is None:
            exchange_symbol = ExchangeSymbol(
                exchange_id=exchange_id,
                asset_id=asset.id,
                symbol=instrument.symbol,
                active=True,
                metadata_json=instrument.metadata,
                last_seen_at=now,
            )
            session.add(exchange_symbol)
        else:
            exchange_symbol.asset_id = asset.id
            exchange_symbol.active = True
            exchange_symbol.metadata_json = instrument.metadata
            exchange_symbol.last_seen_at = now

    async def refresh_comparable_flags(self, session: AsyncSession) -> None:
        await session.execute(update(Asset).values(comparable=False))
        common_ids = select(ExchangeSymbol.asset_id).where(ExchangeSymbol.active.is_(True)).group_by(
            ExchangeSymbol.asset_id
        ).having(func.count(func.distinct(ExchangeSymbol.exchange_id)) >= 2)
        await session.execute(
            update(Asset).where(Asset.id.in_(common_ids)).values(comparable=True)
        )

    async def list_comparable(self, session: AsyncSession) -> list[Asset]:
        result = await session.scalars(
            select(Asset).where(Asset.comparable.is_(True)).order_by(Asset.base_asset)
        )
        return list(result)

    async def load_catalog_rows(
        self, session: AsyncSession
    ) -> list[tuple[int, str, str, str, int, str, str]]:
        statement = (
            select(
                Asset.id,
                Asset.base_asset,
                Asset.quote_asset,
                Asset.contract_type,
                Exchange.id,
                Exchange.code,
                ExchangeSymbol.symbol,
            )
            .join(ExchangeSymbol, ExchangeSymbol.asset_id == Asset.id)
            .join(Exchange, Exchange.id == ExchangeSymbol.exchange_id)
            .where(
                Asset.comparable.is_(True),
                ExchangeSymbol.active.is_(True),
                Exchange.enabled.is_(True),
            )
        )
        return list((await session.execute(statement)).all())
