"""Encrypted transactional email queue."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "c693a17e4d08"
down_revision = "b531d7e28a22"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("email_outbox", sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=True), sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_error", sa.Text()))
    op.create_index("ix_email_outbox_status", "email_outbox", ["status"])


def downgrade():
    op.drop_index("ix_email_outbox_status", table_name="email_outbox")
    op.drop_table("email_outbox")
