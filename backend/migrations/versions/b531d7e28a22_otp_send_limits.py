"""Track OTP send windows without changing previously applied migrations."""
from alembic import op
import sqlalchemy as sa

revision = "b531d7e28a22"
down_revision = "a42c7f3e9810"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("email_verification_otps", "password_reset_otps"):
        op.add_column(table, sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        op.add_column(table, sa.Column("send_count", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    for table in ("email_verification_otps", "password_reset_otps"):
        op.drop_column(table, "send_count")
        op.drop_column(table, "window_started_at")
