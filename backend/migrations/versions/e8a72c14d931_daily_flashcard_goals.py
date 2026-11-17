"""Track the daily flashcard set without changing historical streaks."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'e8a72c14d931'
down_revision = 'd4e9b137c802'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('daily_flashcard_goals',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('activity_date', sa.Date(), primary_key=True),
        sa.Column('saved_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_table('daily_flashcard_goals')
