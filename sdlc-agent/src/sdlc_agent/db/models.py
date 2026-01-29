# =============================================================================
# SDLC Agent - Core Database Models
# =============================================================================

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sdlc_agent.db.base import AuditMixin, Base, UUIDMixin


# =============================================================================
# Enums
# =============================================================================


class ProjectStatus(str, enum.Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    """Task status within a workflow."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, enum.Enum):
    """Task priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(str, enum.Enum):
    """Types of tasks in SDLC."""

    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    SPIKE = "spike"


class AgentType(str, enum.Enum):
    """Types of agents in the system."""

    ORCHESTRATOR = "orchestrator"
    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    CODE_REVIEW = "code_review"
    TESTER = "tester"
    SECURITY = "security"
    DEVOPS = "devops"
    MONITORING = "monitoring"


# =============================================================================
# Models
# =============================================================================


class Project(Base, UUIDMixin, AuditMixin):
    """Software project being managed by the SDLC system."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProjectStatus.ACTIVE,
        nullable=False,
    )

    # Repository information
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    repository_branch: Mapped[str] = mapped_column(
        String(255), default="main", nullable=False
    )

    # Configuration
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_created_at", "created_at"),
    )


class Workflow(Base, UUIDMixin, AuditMixin):
    """Workflow representing an SDLC process execution."""

    __tablename__ = "workflows"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, values_callable=lambda x: [e.value for e in x]),
        default=WorkflowStatus.PENDING,
        nullable=False,
    )

    # Execution tracking
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # State management (LangGraph checkpoint)
    current_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    checkpoint_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="workflows")
    executions: Mapped[list["AgentExecution"]] = relationship(
        "AgentExecution", back_populates="workflow", cascade="all, delete-orphan"
    )
    human_inputs: Mapped[list["HumanInput"]] = relationship(
        "HumanInput", back_populates="workflow", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_workflows_project_id", "project_id"),
        Index("ix_workflows_status", "status"),
        Index("ix_workflows_created_at", "created_at"),
    )


class Task(Base, UUIDMixin, AuditMixin):
    """Task representing work items (epics, stories, tasks)."""

    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Task details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, values_callable=lambda x: [e.value for e in x]),
        default=TaskType.TASK,
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=TaskStatus.BACKLOG,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, values_callable=lambda x: [e.value for e in x]),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )

    # Estimation and tracking
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_hours: Mapped[float | None] = mapped_column(nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(nullable=True)

    # Acceptance criteria (for stories)
    acceptance_criteria: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # Technical details
    technical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # External references
    external_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Jira, GitHub issue, etc.

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    parent: Mapped["Task | None"] = relationship(
        "Task", remote_side="Task.id", back_populates="children"
    )
    children: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_parent_id", "parent_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_task_type", "task_type"),
        Index("ix_tasks_priority", "priority"),
    )


class AgentExecution(Base, UUIDMixin):
    """Record of an agent's execution within a workflow."""

    __tablename__ = "agent_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Execution details
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Input/Output
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Status
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="executions"
    )

    __table_args__ = (
        Index("ix_agent_executions_workflow_id", "workflow_id"),
        Index("ix_agent_executions_agent_type", "agent_type"),
        Index("ix_agent_executions_started_at", "started_at"),
    )


class HumanInput(Base, UUIDMixin):
    """Human-in-the-loop input requests and responses."""

    __tablename__ = "human_inputs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Request details
    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # approval, feedback, clarification
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Response
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    responded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timing
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="human_inputs"
    )

    __table_args__ = (
        Index("ix_human_inputs_workflow_id", "workflow_id"),
        Index("ix_human_inputs_is_resolved", "is_resolved"),
        Index("ix_human_inputs_requested_at", "requested_at"),
    )


class Artifact(Base, UUIDMixin, AuditMixin):
    """Generated artifacts (code, tests, docs, etc.)."""

    __tablename__ = "artifacts"

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Artifact details
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # code, test, doc, config, etc.
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Content (for small artifacts stored in DB)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Extra data (renamed from 'metadata' which is reserved in SQLAlchemy)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    task: Mapped["Task | None"] = relationship("Task", back_populates="artifacts")

    __table_args__ = (
        Index("ix_artifacts_task_id", "task_id"),
        Index("ix_artifacts_artifact_type", "artifact_type"),
        Index("ix_artifacts_name", "name"),
    )


class AuditLog(Base, UUIDMixin):
    """Immutable audit log for compliance and debugging."""

    __tablename__ = "audit_logs"

    # Actor
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # user, agent, system

    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Details
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Request context
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_correlation_id", "correlation_id"),
    )
