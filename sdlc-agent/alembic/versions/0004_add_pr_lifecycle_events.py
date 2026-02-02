"""Add PR lifecycle events table

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Create PR lifecycle stage enum if it doesn't exist
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE prlifecyclestage AS ENUM (
                'created', 'ci_running', 'ci_passed', 'ci_failed',
                'code_review_pending', 'code_review_in_progress',
                'code_review_approved', 'code_review_changes_requested',
                'quality_check_running', 'quality_check_passed', 'quality_check_failed',
                'security_scan_running', 'security_scan_passed', 'security_scan_failed',
                'ready_to_merge', 'merging', 'merged', 'closed'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create actor type enum if it doesn't exist
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE prlifecycleactortype AS ENUM ('user', 'bot', 'ci');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Check if table exists
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'pr_lifecycle_events'"))
    if not result.fetchone():
        # Create pr_lifecycle_events table using raw SQL to avoid SQLAlchemy enum handling
        conn.execute(sa.text("""
            CREATE TABLE pr_lifecycle_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pr_number INTEGER NOT NULL,
                repository VARCHAR(255) NOT NULL,
                stage prlifecyclestage NOT NULL,
                actor_type prlifecycleactortype NOT NULL,
                actor_name VARCHAR(255) NOT NULL,
                actor_avatar_url VARCHAR(500),
                message TEXT,
                details JSONB NOT NULL DEFAULT '{}',
                links JSONB NOT NULL DEFAULT '[]',
                timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        
        # Create indexes
        conn.execute(sa.text("CREATE INDEX ix_pr_lifecycle_events_pr_number ON pr_lifecycle_events (pr_number)"))
        conn.execute(sa.text("CREATE INDEX ix_pr_lifecycle_events_repository ON pr_lifecycle_events (repository)"))
        conn.execute(sa.text("CREATE INDEX ix_pr_lifecycle_events_stage ON pr_lifecycle_events (stage)"))
        conn.execute(sa.text("CREATE INDEX ix_pr_lifecycle_events_timestamp ON pr_lifecycle_events (timestamp)"))
        conn.execute(sa.text("CREATE INDEX ix_pr_lifecycle_events_pr_repo ON pr_lifecycle_events (pr_number, repository)"))
    
    conn.commit()


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_pr_lifecycle_events_pr_repo')
    op.drop_index('ix_pr_lifecycle_events_timestamp')
    op.drop_index('ix_pr_lifecycle_events_stage')
    op.drop_index('ix_pr_lifecycle_events_repository')
    op.drop_index('ix_pr_lifecycle_events_pr_number')
    
    # Drop table
    op.drop_table('pr_lifecycle_events')
    
    # Drop enums
    sa.Enum(name='prlifecycleactortype').drop(op.get_bind())
    sa.Enum(name='prlifecyclestage').drop(op.get_bind())
