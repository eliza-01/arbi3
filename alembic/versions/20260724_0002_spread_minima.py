"""Add spread minima and reset incompatible spread history.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_0002"
down_revision = "20260724_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Previous versions persisted both directions for every quote pair. The new
    # history stores only the best executable ask -> bid arbitrage route, so the
    # old spread history is not semantically compatible.
    op.execute(sa.text("DELETE FROM spread_buckets"))
    op.execute(sa.text("DELETE FROM spread_peaks"))

    op.add_column(
        "spread_buckets",
        sa.Column("min_delta_pct", sa.Numeric(20, 10), nullable=False),
    )
    op.add_column(
        "spread_buckets",
        sa.Column("min_delta_abs", sa.Numeric(32, 12), nullable=False),
    )
    op.add_column(
        "spread_buckets",
        sa.Column("min_observed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column(
        "spread_peaks",
        sa.Column("all_time_min_delta_pct", sa.Numeric(20, 10), nullable=True),
    )
    op.add_column(
        "spread_peaks",
        sa.Column("all_time_min_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "spread_peaks",
        sa.Column("day_min_delta_pct", sa.Numeric(20, 10), nullable=True),
    )
    op.add_column(
        "spread_peaks",
        sa.Column("day_min_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "spread_peaks",
        sa.Column("hour_min_delta_pct", sa.Numeric(20, 10), nullable=True),
    )
    op.add_column(
        "spread_peaks",
        sa.Column("hour_min_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("spread_peaks", "hour_min_at")
    op.drop_column("spread_peaks", "hour_min_delta_pct")
    op.drop_column("spread_peaks", "day_min_at")
    op.drop_column("spread_peaks", "day_min_delta_pct")
    op.drop_column("spread_peaks", "all_time_min_at")
    op.drop_column("spread_peaks", "all_time_min_delta_pct")
    op.drop_column("spread_buckets", "min_observed_at")
    op.drop_column("spread_buckets", "min_delta_abs")
    op.drop_column("spread_buckets", "min_delta_pct")
