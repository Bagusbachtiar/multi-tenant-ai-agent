"""add embedding column to chunks

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("embedding", Vector(768), nullable=True))
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding")
    op.drop_column("chunks", "embedding")
