"""create tenants table and RLS infrastructure

Revision ID: 0001
Revises:
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    op.create_table(
        "tenants",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.UniqueConstraint("api_key_hash", name="uq_tenants_api_key_hash"),
    )

    # Reusable helper: all RLS policies on tenant-scoped tables call this.
    # current_setting(..., true) returns NULL (not error) when var is unset —
    # which causes the policy to match nothing, a safe default.
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid AS $$
            SELECT current_setting('app.current_tenant_id', true)::uuid
        $$ LANGUAGE sql STABLE SECURITY DEFINER;
    """)

    # tenants table itself has no RLS: it must be readable before tenant
    # context is established (during API key lookup in auth).
    # Future tenant-scoped tables use this pattern in their own migrations:
    #
    #   ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
    #   CREATE POLICY tenant_isolation ON <table>
    #       USING (tenant_id = current_tenant_id());


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id()")
    op.drop_table("tenants")
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
