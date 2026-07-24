"""Initial schema.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code", name="uq_exchanges_code"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_asset", sa.String(32), nullable=False),
        sa.Column("quote_asset", sa.String(32), nullable=False),
        sa.Column("contract_type", sa.String(32), nullable=False),
        sa.Column("comparable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "base_asset", "quote_asset", "contract_type", name="uq_assets_contract"
        ),
        sa.Index("ix_assets_comparable", "comparable"),
    )
    op.create_table(
        "exchange_symbols",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("exchange_id", "symbol", name="uq_exchange_symbols_symbol"),
        sa.UniqueConstraint("exchange_id", "asset_id", name="uq_exchange_symbols_asset"),
        sa.Index("ix_exchange_symbols_active", "active"),
    )
    op.create_table(
        "favorites",
        sa.Column("asset_id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "spread_buckets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("buy_exchange_id", sa.Integer(), nullable=False),
        sa.Column("sell_exchange_id", sa.Integer(), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_delta_pct", sa.Numeric(20, 10), nullable=False),
        sa.Column("max_delta_abs", sa.Numeric(32, 12), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buy_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sell_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "asset_id", "buy_exchange_id", "sell_exchange_id", "bucket_start",
            name="uq_spread_buckets_direction_minute",
        ),
        sa.Index("ix_spread_buckets_window", "bucket_start", "asset_id"),
    )
    op.create_table(
        "spread_peaks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("buy_exchange_id", sa.Integer(), nullable=False),
        sa.Column("sell_exchange_id", sa.Integer(), nullable=False),
        sa.Column("all_time_delta_pct", sa.Numeric(20, 10), nullable=True),
        sa.Column("all_time_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("day_delta_pct", sa.Numeric(20, 10), nullable=True),
        sa.Column("day_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hour_delta_pct", sa.Numeric(20, 10), nullable=True),
        sa.Column("hour_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buy_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sell_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "asset_id", "buy_exchange_id", "sell_exchange_id",
            name="uq_spread_peaks_direction",
        ),
    )


def downgrade() -> None:
    op.drop_table("spread_peaks")
    op.drop_table("spread_buckets")
    op.drop_table("favorites")
    op.drop_table("exchange_symbols")
    op.drop_table("assets")
    op.drop_table("exchanges")
