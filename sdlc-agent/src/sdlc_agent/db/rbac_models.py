# =============================================================================
# SDLC Agent - RBAC Database Models
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
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sdlc_agent.db.base import AuditMixin, Base, TimestampMixin, UUIDMixin


# =============================================================================
# Enums
# =============================================================================


class UserStatus(str, enum.Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class RoleType(str, enum.Enum):
    """Type of role (system vs custom)."""

    SYSTEM = "system"  # Built-in roles that cannot be deleted
    CUSTOM = "custom"  # User-created roles


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    # Auth actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    PASSWORD_RESET_FAILED = "password_reset_failed"
    TOKEN_REFRESHED = "token_refreshed"

    # User actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_SUSPENDED = "user_suspended"

    # Role actions
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Permission actions
    PERMISSION_CREATED = "permission_created"
    PERMISSION_UPDATED = "permission_updated"
    PERMISSION_DELETED = "permission_deleted"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"

    # Access actions
    ACCESS_DENIED = "access_denied"
    ACCESS_GRANTED = "access_granted"


# =============================================================================
# RBAC Models
# =============================================================================


class User(Base, UUIDMixin, AuditMixin):
    """User account for authentication and authorization."""

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, values_callable=lambda x: [e.value for e in x]),
        default=UserStatus.PENDING_VERIFICATION,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Settings
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_status", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    @property
    def roles(self) -> list["Role"]:
        """Get all roles assigned to this user."""
        return [ur.role for ur in self.user_roles]

    @property
    def permissions(self) -> set[str]:
        """Get all permission codes for this user."""
        if self.is_superuser:
            return {"*"}  # Superuser has all permissions
        perms = set()
        for role in self.roles:
            for rp in role.role_permissions:
                perms.add(rp.permission.code)
        return perms


class Role(Base, UUIDMixin, AuditMixin):
    """Role for grouping permissions."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_type: Mapped[RoleType] = mapped_column(
        Enum(RoleType, values_callable=lambda x: [e.value for e in x]),
        default=RoleType.CUSTOM,
        nullable=False,
    )

    # Priority (for conflict resolution - higher is more privileged)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_roles_name", "name"),
        Index("ix_roles_role_type", "role_type"),
    )

    @property
    def permissions(self) -> list["Permission"]:
        """Get all permissions for this role."""
        return [rp.permission for rp in self.role_permissions]


class Permission(Base, UUIDMixin, AuditMixin):
    """Permission for fine-grained access control.

    Permission code format: resource:action:scope
    Examples:
        - projects:read:own      - Read own projects
        - projects:read:any      - Read any project
        - projects:write:own     - Write own projects
        - projects:delete:any    - Delete any project
        - users:*:any            - All actions on users
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resource categorization
    resource: Mapped[str] = mapped_column(String(50), nullable=False)  # projects, users, etc.
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # read, write, delete, etc.
    scope: Mapped[str] = mapped_column(String(20), default="own", nullable=False)  # own, any

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_permissions_code", "code"),
        Index("ix_permissions_resource", "resource"),
        Index("ix_permissions_resource_action", "resource", "action"),
    )


class UserRole(Base, UUIDMixin, TimestampMixin):
    """Association table for User-Role many-to-many relationship."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Assignment metadata
    assigned_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
    )


class RolePermission(Base, UUIDMixin, TimestampMixin):
    """Association table for Role-Permission many-to-many relationship."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Grant metadata
    granted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_permissions"
    )

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        Index("ix_role_permissions_role_id", "role_id"),
        Index("ix_role_permissions_permission_id", "permission_id"),
    )


class RBACAuditLog(Base, UUIDMixin):
    """Immutable audit log for RBAC-related actions."""

    __tablename__ = "rbac_audit_logs"

    # Actor information
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[str] = mapped_column(
        String(50), default="user", nullable=False
    )  # user, system, agent

    # Action details
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Target resource
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Details (before/after state, additional context)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Timestamp (immutable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_rbac_audit_logs_actor_id", "actor_id"),
        Index("ix_rbac_audit_logs_action", "action"),
        Index("ix_rbac_audit_logs_resource_type", "resource_type"),
        Index("ix_rbac_audit_logs_timestamp", "timestamp"),
        Index("ix_rbac_audit_logs_correlation_id", "correlation_id"),
    )
