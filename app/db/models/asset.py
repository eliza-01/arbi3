from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("base_asset", "quote_asset", "contract_type", name="uq_assets_contract"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    base_asset: Mapped[str] = mapped_column(String(32))
    quote_asset: Mapped[str] = mapped_column(String(32))
    contract_type: Mapped[str] = mapped_column(String(32))
    comparable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
