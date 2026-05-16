"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-15
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            email TEXT UNIQUE,
            display_name TEXT,
            auth_provider TEXT NOT NULL,
            provider_subject TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE chat_sessions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mode TEXT NOT NULL DEFAULT 'think_clearly',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE chat_messages (
            id UUID PRIMARY KEY,
            session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            safety_level TEXT NOT NULL DEFAULT 'low',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memories (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            importance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            unsafe BOOLEAN NOT NULL DEFAULT false,
            embedding vector(1536),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute(
        """
        CREATE TABLE guidance_rules (
            id UUID PRIMARY KEY,
            topic TEXT NOT NULL,
            tags TEXT[] NOT NULL DEFAULT '{}',
            goal TEXT NOT NULL,
            do_rules TEXT[] NOT NULL DEFAULT '{}',
            avoid_rules TEXT[] NOT NULL DEFAULT '{}',
            tone TEXT NOT NULL DEFAULT 'calm, direct, practical',
            safety_level TEXT NOT NULL DEFAULT 'low',
            priority INTEGER NOT NULL DEFAULT 0,
            approved_by TEXT,
            active BOOLEAN NOT NULL DEFAULT true,
            embedding vector(1536),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE safety_events (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
            level TEXT NOT NULL,
            reasons TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE subscriptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            platform TEXT NOT NULL,
            entitlement TEXT NOT NULL DEFAULT 'free',
            status TEXT NOT NULL DEFAULT 'inactive',
            store_transaction_id TEXT,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE mood_checkins (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            intensity INTEGER,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reset_sessions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reset_type TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT false,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
        """
    )


def downgrade() -> None:
    for table in [
        "reset_sessions",
        "mood_checkins",
        "subscriptions",
        "safety_events",
        "guidance_rules",
        "memories",
        "chat_messages",
        "chat_sessions",
        "users",
    ]:
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS vector")
