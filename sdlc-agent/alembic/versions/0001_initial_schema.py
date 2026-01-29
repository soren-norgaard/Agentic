"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE projectstatus AS ENUM ('active', 'paused', 'completed', 'archived')")
    op.execute("CREATE TYPE workflowstatus AS ENUM ('pending', 'running', 'paused', 'awaiting_input', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE taskstatus AS ENUM ('backlog', 'todo', 'in_progress', 'in_review', 'done', 'blocked')")
    op.execute("CREATE TYPE taskpriority AS ENUM ('critical', 'high', 'medium', 'low')")
    op.execute("CREATE TYPE tasktype AS ENUM ('epic', 'story', 'task', 'bug', 'spike')")
    op.execute("CREATE TYPE agenttype AS ENUM ('orchestrator', 'requirements', 'planning', 'architect', 'developer', 'code_review', 'tester', 'security', 'devops', 'monitoring')")

    # Projects table
    op.create_table('projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'completed', 'archived', name='projectstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('repository_url', sa.String(length=500), nullable=True),
        sa.Column('repository_branch', sa.String(length=255), nullable=False, server_default='main'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_projects_created_at', 'projects', ['created_at'], unique=False)
    op.create_index('ix_projects_status', 'projects', ['status'], unique=False)

    # Tasks table
    op.create_table('tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', postgresql.ENUM('epic', 'story', 'task', 'bug', 'spike', name='tasktype', create_type=False), nullable=False, server_default='task'),
        sa.Column('status', postgresql.ENUM('backlog', 'todo', 'in_progress', 'in_review', 'done', 'blocked', name='taskstatus', create_type=False), nullable=False, server_default='backlog'),
        sa.Column('priority', postgresql.ENUM('critical', 'high', 'medium', 'low', name='taskpriority', create_type=False), nullable=False, server_default='medium'),
        sa.Column('story_points', sa.Integer(), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('acceptance_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('technical_notes', sa.Text(), nullable=True),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_parent_id', 'tasks', ['parent_id'], unique=False)
    op.create_index('ix_tasks_priority', 'tasks', ['priority'], unique=False)
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'], unique=False)
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)
    op.create_index('ix_tasks_task_type', 'tasks', ['task_type'], unique=False)

    # Workflows table
    op.create_table('workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'paused', 'awaiting_input', 'completed', 'failed', 'cancelled', name='workflowstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('checkpoint_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflows_created_at', 'workflows', ['created_at'], unique=False)
    op.create_index('ix_workflows_project_id', 'workflows', ['project_id'], unique=False)
    op.create_index('ix_workflows_status', 'workflows', ['status'], unique=False)

    # Agent Executions table
    op.create_table('agent_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('agent_type', postgresql.ENUM('orchestrator', 'requirements', 'planning', 'architect', 'developer', 'code_review', 'tester', 'security', 'devops', 'monitoring', name='agenttype', create_type=False), nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('iterations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_executions_agent_type', 'agent_executions', ['agent_type'], unique=False)
    op.create_index('ix_agent_executions_started_at', 'agent_executions', ['started_at'], unique=False)
    op.create_index('ix_agent_executions_workflow_id', 'agent_executions', ['workflow_id'], unique=False)

    # Artifacts table
    op.create_table('artifacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('storage_url', sa.String(length=1000), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_artifacts_artifact_type', 'artifacts', ['artifact_type'], unique=False)
    op.create_index('ix_artifacts_name', 'artifacts', ['name'], unique=False)
    op.create_index('ix_artifacts_task_id', 'artifacts', ['task_id'], unique=False)

    # Human Inputs table
    op.create_table('human_inputs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('responded_by', sa.String(length=255), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_human_inputs_is_resolved', 'human_inputs', ['is_resolved'], unique=False)
    op.create_index('ix_human_inputs_requested_at', 'human_inputs', ['requested_at'], unique=False)
    op.create_index('ix_human_inputs_workflow_id', 'human_inputs', ['workflow_id'], unique=False)

    # Audit Logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.String(length=255), nullable=True),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('correlation_id', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_correlation_id', 'audit_logs', ['correlation_id'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('human_inputs')
    op.drop_table('artifacts')
    op.drop_table('agent_executions')
    op.drop_table('workflows')
    op.drop_table('tasks')
    op.drop_table('projects')
    op.execute("DROP TYPE agenttype")
    op.execute("DROP TYPE tasktype")
    op.execute("DROP TYPE taskpriority")
    op.execute("DROP TYPE taskstatus")
    op.execute("DROP TYPE workflowstatus")
    op.execute("DROP TYPE projectstatus")
