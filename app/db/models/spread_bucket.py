from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpreadBucket(Base):
    __tablename__ = "spread_buckets"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "buy_exchange_id",
            "sell_exchange_id",
            "bucket_start",
            name="uq_spread_buckets_direction_minute",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    buy_exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id", ondelete="CASCADE")
    )
    sell_exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id", ondelete="CASCADE")
    )
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    max_delta_pct: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    max_delta_abs: Mapped[Decimal] = mapped_column(Numeric(32, 12))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    min_delta_pct: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    min_delta_abs: Mapped[Decimal] = mapped_column(Numeric(32, 12))
    min_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
