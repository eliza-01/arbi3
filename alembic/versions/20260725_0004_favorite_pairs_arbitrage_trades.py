"""Favorite exchange pairs and manual arbitrage trades.

Revision ID: 20260725_0004
Revises: 20260724_0003
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa

revision = "20260725_0004"
down_revision = "20260724_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorite_pairs",
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("exchange_a_id", sa.Integer(), nullable=False),
        sa.Column("exchange_b_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("exchange_a_id < exchange_b_id", name="ck_favorite_pairs_order"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exchange_a_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exchange_b_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "exchange_a_id", "exchange_b_id"),
    )
    # Preserve old asset-level favorites by expanding them to every currently
    # comparable exchange pair for that asset.
    op.execute(
        """
        INSERT IGNORE INTO favorite_pairs (asset_id, exchange_a_id, exchange_b_id, created_at)
        SELECT f.asset_id, left_symbol.exchange_id, right_symbol.exchange_id, f.created_at
        FROM favorites f
        JOIN exchange_symbols left_symbol
          ON left_symbol.asset_id = f.asset_id AND left_symbol.active = 1
        JOIN exchange_symbols right_symbol
          ON right_symbol.asset_id = f.asset_id
         AND right_symbol.active = 1
         AND left_symbol.exchange_id < right_symbol.exchange_id
        """
    )

    op.create_table(
        "arbitrage_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("exchange_a_id", sa.Integer(), nullable=False),
        sa.Column("exchange_b_id", sa.Integer(), nullable=False),
        sa.Column("buy_exchange_id", sa.Integer(), nullable=False),
        sa.Column("sell_exchange_id", sa.Integer(), nullable=False),
        sa.Column("buy_symbol", sa.String(64), nullable=False),
        sa.Column("sell_symbol", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("position_usdt", sa.Numeric(24, 8), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("rounding", sa.String(8), nullable=False),
        sa.Column("insurance_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("buy_quantity", sa.Numeric(32, 12), nullable=True),
        sa.Column("sell_quantity", sa.Numeric(32, 12), nullable=True),
        sa.Column("buy_order_id", sa.String(128), nullable=True),
        sa.Column("sell_order_id", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exchange_a_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exchange_b_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buy_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sell_exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.Index("ix_arbitrage_trades_pair_status", "asset_id", "exchange_a_id", "exchange_b_id", "status"),
        sa.Index("ix_arbitrage_trades_status_updated", "status", "updated_at"),
    )


def downgrade() -> None:
    op.drop_table("arbitrage_trades")
    op.drop_table("favorite_pairs")
