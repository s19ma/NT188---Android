"""Store one learning activity per user and Vietnam calendar day."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f31a7c4d2e01"
down_revision = "e7b2c9d4a6f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("learning_days",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("activity_date", sa.Date(), primary_key=True))


def downgrade():
    op.drop_table("learning_days")
