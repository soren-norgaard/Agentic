# =============================================================================
# SDLC Agent - Database Module
# =============================================================================

from sdlc_agent.db.base import AuditMixin, Base, TimestampMixin, UUIDMixin
from sdlc_agent.db.engine import (
    close_db,
    get_engine,
    get_session,
    get_session_context,
    get_session_factory,
    init_db,
)
from sdlc_agent.db.models import (
    AgentExecution,
    AgentType,
    Artifact,
    AuditLog,
    HumanInput,
    PRLifecycleActorType,
    PRLifecycleEvent,
    PRLifecycleStage,
    Project,
    ProjectStatus,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
    Workflow,
    WorkflowStatus,
)
from sdlc_agent.db.rbac_models import (
    AuditAction,
    Permission,
    RBACAuditLog,
    Role,
    RolePermission,
    RoleType,
    User,
    UserRole,
    UserStatus,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "AuditMixin",
    # Engine
    "get_engine",
    "get_session_factory",
    "get_session",
    "get_session_context",
    "init_db",
    "close_db",
    # Enums
    "ProjectStatus",
    "WorkflowStatus",
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "AgentType",
    # Models
    "Project",
    "Workflow",
    "Task",
    "AgentExecution",
    "HumanInput",
    "Artifact",
    "AuditLog",
    "PRLifecycleEvent",
    # PR Lifecycle Enums
    "PRLifecycleStage",
    "PRLifecycleActorType",
    # RBAC Enums
    "UserStatus",
    "RoleType",
    "AuditAction",
    # RBAC Models
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "RBACAuditLog",
]
