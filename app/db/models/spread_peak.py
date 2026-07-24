from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpreadPeak(Base):
    __tablename__ = "spread_peaks"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "buy_exchange_id", "sell_exchange_id", name="uq_spread_peaks_direction"
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
    all_time_delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    all_time_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    all_time_min_delta_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10), nullable=True
    )
    all_time_min_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    day_delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    day_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    day_min_delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    day_min_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hour_delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    hour_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hour_min_delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    hour_min_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
