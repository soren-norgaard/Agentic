# =============================================================================
# SDLC Agent - RBAC Dependencies
# =============================================================================

from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sdlc_agent.core.auth import (
    TokenData,
    check_permission,
    verify_access_token,
)
from sdlc_agent.core.exceptions import AuthenticationError, AuthorizationError
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import User, UserRole, UserStatus


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get the current authenticated user from the JWT token.

    Args:
        authorization: Authorization header with Bearer token
        session: Database session

    Returns:
        Authenticated User object

    Raises:
        AuthenticationError: If token is missing, invalid, or user not found
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    token = parts[1]

    # Verify token
    token_data = verify_access_token(token)

    # Get user from database
    query = select(User).where(User.id == token_data.sub).options(
        selectinload(User.user_roles)
        .selectinload(UserRole.role)
        .selectinload("role_permissions")
        .selectinload("permission")
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError(f"User account is {user.status.value}")

    return user


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Get the current user if authenticated, None otherwise.

    Useful for endpoints that have different behavior for authenticated vs anonymous users.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, session)
    except AuthenticationError:
        return None


def require_permission(permission: str) -> Callable:
    """Create a dependency that requires a specific permission.

    Usage:
        @router.get("/protected")
        async def protected_route(
            _: Annotated[None, Depends(require_permission("projects:read:any"))]
        ):
            ...

    Args:
        permission: Permission code to require (e.g., "projects:read:any")

    Returns:
        Dependency function that validates the permission
    """
    async def _require_permission(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        user_permissions = current_user.permissions

        if not check_permission(user_permissions, permission):
            raise AuthorizationError(
                f"Permission denied: requires '{permission}'"
            )

    return _require_permission


def require_any_permission(permissions: list[str]) -> Callable:
    """Create a dependency that requires any one of the specified permissions.

    Usage:
        @router.get("/protected")
        async def protected_route(
            _: Annotated[None, Depends(require_any_permission(["projects:read:own", "projects:read:any"]))]
        ):
            ...

    Args:
        permissions: List of permission codes (any one is sufficient)

    Returns:
        Dependency function that validates at least one permission
    """
    async def _require_any_permission(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        user_permissions = current_user.permissions

        for perm in permissions:
            if check_permission(user_permissions, perm):
                return

        raise AuthorizationError(
            f"Permission denied: requires one of {permissions}"
        )

    return _require_any_permission


def require_all_permissions(permissions: list[str]) -> Callable:
    """Create a dependency that requires all specified permissions.

    Usage:
        @router.get("/protected")
        async def protected_route(
            _: Annotated[None, Depends(require_all_permissions(["projects:read:any", "tasks:read:any"]))]
        ):
            ...

    Args:
        permissions: List of permission codes (all required)

    Returns:
        Dependency function that validates all permissions
    """
    async def _require_all_permissions(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        user_permissions = current_user.permissions

        for perm in permissions:
            if not check_permission(user_permissions, perm):
                raise AuthorizationError(
                    f"Permission denied: requires '{perm}'"
                )

    return _require_all_permissions


def require_role(role_name: str) -> Callable:
    """Create a dependency that requires a specific role.

    Usage:
        @router.get("/admin")
        async def admin_route(
            _: Annotated[None, Depends(require_role("admin"))]
        ):
            ...

    Args:
        role_name: Name of the required role

    Returns:
        Dependency function that validates the role
    """
    async def _require_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        user_roles = {ur.role.name for ur in current_user.user_roles if ur.role.is_active}

        # Superuser has all roles implicitly
        if current_user.is_superuser:
            return

        if role_name not in user_roles:
            raise AuthorizationError(
                f"Permission denied: requires role '{role_name}'"
            )

    return _require_role


def require_any_role(role_names: list[str]) -> Callable:
    """Create a dependency that requires any one of the specified roles.

    Args:
        role_names: List of role names (any one is sufficient)

    Returns:
        Dependency function that validates at least one role
    """
    async def _require_any_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        # Superuser has all roles implicitly
        if current_user.is_superuser:
            return

        user_roles = {ur.role.name for ur in current_user.user_roles if ur.role.is_active}

        for role in role_names:
            if role in user_roles:
                return

        raise AuthorizationError(
            f"Permission denied: requires one of roles {role_names}"
        )

    return _require_any_role
