"""Initial schema: twitch_tokens and twitch_channels.

Revision ID: 001
Revises:
Create Date: 2026-08-30

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "twitch_tokens",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        if_not_exists=True,
    )
    op.create_table(
        "twitch_channels",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("login", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("channel_type", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["twitch_tokens.user_id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "channel_type IN ('owner', 'bot', 'public')",
            name="twitch_channels_channel_type_check",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "twitch_channels_active_idx",
        "twitch_channels",
        ["is_active"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("twitch_channels_active_idx", table_name="twitch_channels", if_exists=True)
    op.drop_table("twitch_channels", if_exists=True)
    op.drop_table("twitch_tokens", if_exists=True)
