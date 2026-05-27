"""profile fact capture policy

Revision ID: 0004_profile_fact_policy
Revises: 0003_encrypt_memory_facts
Create Date: 2026-05-27
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0004_profile_fact_policy"
down_revision: Union[str, None] = "0003_encrypt_memory_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE profile_fact_capture_policy (
            id TEXT PRIMARY KEY DEFAULT 'default',
            capture_terms JSONB NOT NULL DEFAULT '{}'::jsonb,
            blocked_terms JSONB NOT NULL DEFAULT '{}'::jsonb,
            ttl_days_by_type JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.drop_table("profile_fact_capture_policy")
