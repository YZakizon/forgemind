"""profile facts

Revision ID: 0002_profile_facts
Revises: 0001_initial_schema
Create Date: 2026-05-26
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0002_profile_facts"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE profile_facts (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            fact_type TEXT NOT NULL,
            label TEXT NOT NULL,
            value TEXT NOT NULL,
            sensitivity TEXT NOT NULL DEFAULT 'normal',
            source TEXT NOT NULL DEFAULT 'chat',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.65,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX profile_facts_user_expires_idx ON profile_facts (user_id, expires_at)")
    op.execute("CREATE UNIQUE INDEX profile_facts_unique_idx ON profile_facts (user_id, fact_type, label, value)")


def downgrade() -> None:
    op.drop_table("profile_facts")
