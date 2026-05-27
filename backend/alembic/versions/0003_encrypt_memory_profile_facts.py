"""encrypt memory profile facts

Revision ID: 0003_encrypt_memory_profile_facts
Revises: 0002_profile_facts
Create Date: 2026-05-26
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0003_encrypt_memory_profile_facts"
down_revision: Union[str, None] = "0002_profile_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_encryption_keys (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            wrapped_dek BYTEA NOT NULL,
            wrap_nonce BYTEA NOT NULL,
            wrap_key_id TEXT NOT NULL,
            algorithm TEXT NOT NULL DEFAULT 'AES-256-GCM',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            rotated_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        ALTER TABLE memories
            ADD COLUMN content_ciphertext BYTEA,
            ADD COLUMN content_nonce BYTEA,
            ADD COLUMN content_key_id TEXT,
            ADD COLUMN content_hash TEXT
        """
    )
    op.execute("CREATE INDEX memories_content_hash_idx ON memories (user_id, content_hash)")
    op.execute(
        """
        ALTER TABLE profile_facts
            ADD COLUMN value_ciphertext BYTEA,
            ADD COLUMN value_nonce BYTEA,
            ADD COLUMN value_key_id TEXT,
            ADD COLUMN value_hash TEXT
        """
    )
    op.execute("DROP INDEX IF EXISTS profile_facts_unique_idx")
    op.execute(
        """
        CREATE UNIQUE INDEX profile_facts_unique_hash_idx
        ON profile_facts (user_id, fact_type, label, value_hash)
        WHERE value_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS profile_facts_unique_hash_idx")
    op.execute("DROP INDEX IF EXISTS memories_content_hash_idx")
    op.execute(
        """
        ALTER TABLE profile_facts
            DROP COLUMN IF EXISTS value_hash,
            DROP COLUMN IF EXISTS value_key_id,
            DROP COLUMN IF EXISTS value_nonce,
            DROP COLUMN IF EXISTS value_ciphertext
        """
    )
    op.execute(
        """
        ALTER TABLE memories
            DROP COLUMN IF EXISTS content_hash,
            DROP COLUMN IF EXISTS content_key_id,
            DROP COLUMN IF EXISTS content_nonce,
            DROP COLUMN IF EXISTS content_ciphertext
        """
    )
    op.drop_table("user_encryption_keys")
    op.execute("CREATE UNIQUE INDEX profile_facts_unique_idx ON profile_facts (user_id, fact_type, label, value)")
