# =============================================================================
# SDLC Agent - RBAC Seed Data
# =============================================================================
# Script to seed default roles, permissions, and admin user.
# Run with: python -m sdlc_agent.db.rbac_seed
# =============================================================================

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.auth import hash_password
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session_context
from sdlc_agent.db.rbac_models import (
    Permission,
    Role,
    RolePermission,
    RoleType,
    User,
    UserRole,
    UserStatus,
)

logger = get_logger(__name__)


# =============================================================================
# Default Permissions
# =============================================================================

DEFAULT_PERMISSIONS: list[dict[str, Any]] = [
    # Project permissions
    {"code": "projects:create:any", "name": "Create Projects", "description": "Create new projects", "resource": "projects", "action": "create", "scope": "any"},
    {"code": "projects:read:own", "name": "Read Own Projects", "description": "Read own projects", "resource": "projects", "action": "read", "scope": "own"},
    {"code": "projects:read:any", "name": "Read Any Project", "description": "Read any project", "resource": "projects", "action": "read", "scope": "any"},
    {"code": "projects:update:own", "name": "Update Own Projects", "description": "Update own projects", "resource": "projects", "action": "update", "scope": "own"},
    {"code": "projects:update:any", "name": "Update Any Project", "description": "Update any project", "resource": "projects", "action": "update", "scope": "any"},
    {"code": "projects:delete:own", "name": "Delete Own Projects", "description": "Delete own projects", "resource": "projects", "action": "delete", "scope": "own"},
    {"code": "projects:delete:any", "name": "Delete Any Project", "description": "Delete any project", "resource": "projects", "action": "delete", "scope": "any"},

    # Workflow permissions
    {"code": "workflows:create:any", "name": "Create Workflows", "description": "Create workflows", "resource": "workflows", "action": "create", "scope": "any"},
    {"code": "workflows:read:own", "name": "Read Own Workflows", "description": "Read own workflows", "resource": "workflows", "action": "read", "scope": "own"},
    {"code": "workflows:read:any", "name": "Read Any Workflow", "description": "Read any workflow", "resource": "workflows", "action": "read", "scope": "any"},
    {"code": "workflows:update:any", "name": "Update Workflows", "description": "Update workflows", "resource": "workflows", "action": "update", "scope": "any"},
    {"code": "workflows:delete:any", "name": "Delete Workflows", "description": "Delete workflows", "resource": "workflows", "action": "delete", "scope": "any"},

    # Task permissions
    {"code": "tasks:create:any", "name": "Create Tasks", "description": "Create tasks", "resource": "tasks", "action": "create", "scope": "any"},
    {"code": "tasks:read:own", "name": "Read Own Tasks", "description": "Read own tasks", "resource": "tasks", "action": "read", "scope": "own"},
    {"code": "tasks:read:any", "name": "Read Any Task", "description": "Read any task", "resource": "tasks", "action": "read", "scope": "any"},
    {"code": "tasks:update:own", "name": "Update Own Tasks", "description": "Update own tasks", "resource": "tasks", "action": "update", "scope": "own"},
    {"code": "tasks:update:any", "name": "Update Any Task", "description": "Update any task", "resource": "tasks", "action": "update", "scope": "any"},
    {"code": "tasks:delete:any", "name": "Delete Tasks", "description": "Delete tasks", "resource": "tasks", "action": "delete", "scope": "any"},

    # User permissions
    {"code": "users:create:any", "name": "Create Users", "description": "Create new users", "resource": "users", "action": "create", "scope": "any"},
    {"code": "users:read:own", "name": "Read Own Profile", "description": "Read own user profile", "resource": "users", "action": "read", "scope": "own"},
    {"code": "users:read:any", "name": "Read Any User", "description": "Read any user profile", "resource": "users", "action": "read", "scope": "any"},
    {"code": "users:update:own", "name": "Update Own Profile", "description": "Update own user profile", "resource": "users", "action": "update", "scope": "own"},
    {"code": "users:update:any", "name": "Update Any User", "description": "Update any user", "resource": "users", "action": "update", "scope": "any"},
    {"code": "users:delete:any", "name": "Delete Users", "description": "Delete users", "resource": "users", "action": "delete", "scope": "any"},

    # Role permissions
    {"code": "roles:create:any", "name": "Create Roles", "description": "Create new roles", "resource": "roles", "action": "create", "scope": "any"},
    {"code": "roles:read:any", "name": "Read Roles", "description": "Read roles", "resource": "roles", "action": "read", "scope": "any"},
    {"code": "roles:update:any", "name": "Update Roles", "description": "Update roles", "resource": "roles", "action": "update", "scope": "any"},
    {"code": "roles:delete:any", "name": "Delete Roles", "description": "Delete roles", "resource": "roles", "action": "delete", "scope": "any"},

    # Permission permissions
    {"code": "permissions:create:any", "name": "Create Permissions", "description": "Create new permissions", "resource": "permissions", "action": "create", "scope": "any"},
    {"code": "permissions:read:any", "name": "Read Permissions", "description": "Read permissions", "resource": "permissions", "action": "read", "scope": "any"},
    {"code": "permissions:update:any", "name": "Update Permissions", "description": "Update permissions", "resource": "permissions", "action": "update", "scope": "any"},
    {"code": "permissions:delete:any", "name": "Delete Permissions", "description": "Delete permissions", "resource": "permissions", "action": "delete", "scope": "any"},

    # Audit permissions
    {"code": "audit:read:any", "name": "Read Audit Logs", "description": "Read audit logs", "resource": "audit", "action": "read", "scope": "any"},

    # Agent permissions
    {"code": "agents:execute:any", "name": "Execute Agents", "description": "Execute AI agents", "resource": "agents", "action": "execute", "scope": "any"},
    {"code": "agents:read:any", "name": "Read Agent Status", "description": "Read agent execution status", "resource": "agents", "action": "read", "scope": "any"},
]


# =============================================================================
# Default Roles
# =============================================================================

DEFAULT_ROLES: list[dict[str, Any]] = [
    {
        "name": "admin",
        "description": "Full system administrator with all permissions",
        "role_type": RoleType.SYSTEM,
        "priority": 100,
        "permissions": ["*"],  # Special: all permissions
    },
    {
        "name": "developer",
        "description": "Developer with project and workflow access",
        "role_type": RoleType.SYSTEM,
        "priority": 50,
        "permissions": [
            "projects:create:any", "projects:read:any", "projects:update:own", "projects:delete:own",
            "workflows:create:any", "workflows:read:any", "workflows:update:any",
            "tasks:create:any", "tasks:read:any", "tasks:update:any",
            "agents:execute:any", "agents:read:any",
            "users:read:own", "users:update:own",
        ],
    },
    {
        "name": "viewer",
        "description": "Read-only access to projects and workflows",
        "role_type": RoleType.SYSTEM,
        "priority": 10,
        "permissions": [
            "projects:read:any",
            "workflows:read:any",
            "tasks:read:any",
            "users:read:own",
        ],
    },
    {
        "name": "guest",
        "description": "Minimal access for unauthenticated or limited users",
        "role_type": RoleType.SYSTEM,
        "priority": 0,
        "permissions": [],  # No permissions, only public endpoints
    },
]


# =============================================================================
# Seed Functions
# =============================================================================


async def seed_permissions(session: AsyncSession) -> dict[str, Permission]:
    """Seed default permissions if they don't exist."""
    logger.info("Seeding default permissions...")

    permissions_map: dict[str, Permission] = {}

    for perm_data in DEFAULT_PERMISSIONS:
        # Check if permission exists
        result = await session.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        permission = result.scalar_one_or_none()

        if not permission:
            permission = Permission(**perm_data)
            session.add(permission)
            logger.info(f"Created permission: {perm_data['code']}")
        else:
            logger.debug(f"Permission exists: {perm_data['code']}")

        permissions_map[perm_data["code"]] = permission

    await session.flush()
    return permissions_map


async def seed_roles(session: AsyncSession, permissions_map: dict[str, Permission]) -> dict[str, Role]:
    """Seed default roles and their permissions."""
    logger.info("Seeding default roles...")

    roles_map: dict[str, Role] = {}

    for role_data in DEFAULT_ROLES:
        role_permissions = role_data.pop("permissions")

        # Check if role exists
        result = await session.execute(
            select(Role).where(Role.name == role_data["name"])
        )
        role = result.scalar_one_or_none()

        if not role:
            role = Role(**role_data, is_active=True)
            session.add(role)
            await session.flush()  # Get the role ID
            logger.info(f"Created role: {role_data['name']}")

            # Assign permissions (skip for admin with "*")
            if role_permissions != ["*"]:
                for perm_code in role_permissions:
                    if perm_code in permissions_map:
                        role_perm = RolePermission(
                            role_id=role.id,
                            permission_id=permissions_map[perm_code].id,
                            granted_by="system",
                        )
                        session.add(role_perm)
                        logger.debug(f"Assigned {perm_code} to {role_data['name']}")
        else:
            logger.debug(f"Role exists: {role_data['name']}")

        roles_map[role_data["name"]] = role

    await session.flush()
    return roles_map


async def seed_admin_user(session: AsyncSession, roles_map: dict[str, Role]) -> User | None:
    """Create default admin user if it doesn't exist."""
    logger.info("Checking for admin user...")

    # Check if admin user exists
    result = await session.execute(
        select(User).where(User.username == "admin")
    )
    admin_user = result.scalar_one_or_none()

    if admin_user:
        logger.info("Admin user already exists")
        return admin_user

    # Create admin user
    admin_user = User(
        email="admin@sdlc-agent.local",
        username="admin",
        full_name="System Administrator",
        password_hash=hash_password("Admin123!"),  # Default password - CHANGE IN PRODUCTION
        status=UserStatus.ACTIVE,
        is_superuser=True,
        email_verified=True,
    )
    session.add(admin_user)
    await session.flush()

    # Assign admin role
    if "admin" in roles_map:
        user_role = UserRole(
            user_id=admin_user.id,
            role_id=roles_map["admin"].id,
            assigned_by="system",
        )
        session.add(user_role)

    logger.info("Created admin user (username: admin, password: Admin123!)")
    logger.warning("⚠️  CHANGE THE DEFAULT ADMIN PASSWORD IN PRODUCTION!")

    return admin_user


async def seed_all() -> None:
    """Seed all default RBAC data."""
    logger.info("Starting RBAC seed process...")

    async with get_session_context() as session:
        # Seed in order: permissions -> roles -> admin user
        permissions_map = await seed_permissions(session)
        roles_map = await seed_roles(session, permissions_map)
        await seed_admin_user(session, roles_map)

        await session.commit()

    logger.info("✅ RBAC seed completed successfully!")


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    asyncio.run(seed_all())
