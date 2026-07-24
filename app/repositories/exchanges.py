from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exchange import Exchange


class ExchangeRepository:
    async def ensure(self, session: AsyncSession, code: str, name: str) -> Exchange:
        exchange = await session.scalar(select(Exchange).where(Exchange.code == code))
        if exchange is None:
            exchange = Exchange(code=code, name=name, enabled=True)
            session.add(exchange)
            await session.flush()
        else:
            exchange.name = name
            exchange.enabled = True
        return exchange

    async def list_enabled(self, session: AsyncSession) -> list[Exchange]:
        result = await session.scalars(select(Exchange).where(Exchange.enabled.is_(True)))
        return list(result)
