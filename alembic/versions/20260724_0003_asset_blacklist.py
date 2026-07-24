"""Add persistent asset blacklist.

Revision ID: 20260724_0003
Revises: 20260724_0002
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260724_0003"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blacklisted_assets",
        sa.Column("asset_id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("blacklisted_assets")
