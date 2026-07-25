from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ArbitrageTrade(Base):
    __tablename__ = "arbitrage_trades"
    __table_args__ = (
        Index(
            "ix_arbitrage_trades_pair_status",
            "asset_id",
            "exchange_a_id",
            "exchange_b_id",
            "status",
        ),
        Index("ix_arbitrage_trades_status_updated", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    exchange_a_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"))
    exchange_b_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"))
    buy_exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"))
    sell_exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"))
    buy_symbol: Mapped[str] = mapped_column(String(64))
    sell_symbol: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    position_usdt: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    leverage: Mapped[int] = mapped_column()
    rounding: Mapped[str] = mapped_column(String(8))
    insurance_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    buy_quantity: Mapped[Decimal | None] = mapped_column(Numeric(32, 12), nullable=True)
    sell_quantity: Mapped[Decimal | None] = mapped_column(Numeric(32, 12), nullable=True)
    buy_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sell_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
