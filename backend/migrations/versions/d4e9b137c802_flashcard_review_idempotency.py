"""Persist idempotent flashcard review results without changing existing schedules."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "d4e9b137c802"
down_revision = "c693a17e4d08"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("flashcard_review_requests",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("saved_id", UUID(as_uuid=True), sa.ForeignKey("user_vocabulary.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.String(10), nullable=False),
        sa.Column("response", JSONB, nullable=False))


def downgrade():
    op.drop_table("flashcard_review_requests")
