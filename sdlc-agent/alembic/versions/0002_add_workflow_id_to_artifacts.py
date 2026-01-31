"""add_workflow_id_to_artifacts

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add workflow_id column to artifacts table
    op.add_column('artifacts', sa.Column('workflow_id', sa.UUID(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_artifacts_workflow_id',
        'artifacts', 'workflows',
        ['workflow_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for workflow_id
    op.create_index('ix_artifacts_workflow_id', 'artifacts', ['workflow_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_artifacts_workflow_id', table_name='artifacts')
    op.drop_constraint('fk_artifacts_workflow_id', 'artifacts', type_='foreignkey')
    op.drop_column('artifacts', 'workflow_id')
