"""Add password reset fields to users table

Revision ID: 0005
Revises: 0004_add_pr_lifecycle_events
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password reset fields to users table
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove password reset fields
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
