"""add Vietnamese vocabulary definitions

Revision ID: f12a8b7c4e3d
Revises: e8a72c14d931
"""
from alembic import op
import sqlalchemy as sa

revision = "f12a8b7c4e3d"
down_revision = "e8a72c14d931"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vocabulary", sa.Column("vietnamese_definition", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vocabulary", "vietnamese_definition")
