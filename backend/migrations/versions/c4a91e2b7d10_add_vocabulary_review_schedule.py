"""add vocabulary learning status and review schedule

Revision ID: c4a91e2b7d10
Revises: 7be83c428a58
Create Date: 2026-11-14 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a91e2b7d10"
down_revision: Union[str, Sequence[str], None] = "7be83c428a58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "learning_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "ease_factor",
            sa.Numeric(4, 2),
            nullable=False,
            server_default=sa.text("2.50"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "interval_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "repetitions",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "review_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "next_review_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "user_vocabulary",
        sa.Column(
            "last_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "user_vocabulary_learning_status_check",
        "user_vocabulary",
        "learning_status::text = ANY (ARRAY['new','learning','learned']::text[])",
    )
    op.create_check_constraint(
        "user_vocabulary_ease_factor_check",
        "user_vocabulary",
        "ease_factor >= 1.3",
    )
    op.create_check_constraint(
        "user_vocabulary_interval_days_check",
        "user_vocabulary",
        "interval_days >= 0",
    )
    op.create_check_constraint(
        "user_vocabulary_repetitions_check",
        "user_vocabulary",
        "repetitions >= 0",
    )
    op.create_check_constraint(
        "user_vocabulary_review_count_check",
        "user_vocabulary",
        "review_count >= 0",
    )
    op.create_index(
        "idx_user_vocabulary_user_review",
        "user_vocabulary",
        ["user_id", "next_review_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_user_vocabulary_user_review", table_name="user_vocabulary")
    op.drop_constraint(
        "user_vocabulary_review_count_check", "user_vocabulary", type_="check"
    )
    op.drop_constraint(
        "user_vocabulary_repetitions_check", "user_vocabulary", type_="check"
    )
    op.drop_constraint(
        "user_vocabulary_interval_days_check", "user_vocabulary", type_="check"
    )
    op.drop_constraint(
        "user_vocabulary_ease_factor_check", "user_vocabulary", type_="check"
    )
    op.drop_constraint(
        "user_vocabulary_learning_status_check", "user_vocabulary", type_="check"
    )
    op.drop_column("user_vocabulary", "last_reviewed_at")
    op.drop_column("user_vocabulary", "next_review_at")
    op.drop_column("user_vocabulary", "review_count")
    op.drop_column("user_vocabulary", "repetitions")
    op.drop_column("user_vocabulary", "interval_days")
    op.drop_column("user_vocabulary", "ease_factor")
    op.drop_column("user_vocabulary", "learning_status")
