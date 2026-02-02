# =============================================================================
# SDLC Agent - User Management Routes
# =============================================================================

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sdlc_agent.api.routes.rbac_deps import get_current_user, require_permission
from sdlc_agent.api.schemas.rbac import (
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserResponse,
    UserRoleAssign,
    UserRoleResponse,
    UserUpdate,
    UserWithRolesResponse,
)
from sdlc_agent.core.auth import hash_password, verify_password
from sdlc_agent.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EntityNotFoundError,
)
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import (
    AuditAction,
    RBACAuditLog,
    Role,
    User,
    UserRole,
    UserStatus,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# User CRUD
# =============================================================================


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:create:any"))],
) -> UserResponse:
    """Create a new user."""
    # Check for existing user
    existing = await session.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if existing.scalar_one_or_none():
        raise AuthorizationError("User with this email or username already exists")

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        status=UserStatus.ACTIVE,
        email_verified=False,
    )
    session.add(user)

    # Log audit
    audit = RBACAuditLog(
        actor_id=None,  # Would be current user in production
        action=AuditAction.USER_CREATED,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(user)

    logger.info(f"Created user {user.username}")
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:read:any"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: UserStatus | None = Query(None, alias="status"),
) -> UserListResponse:
    """List all users with pagination."""
    # Count query
    count_query = select(func.count()).select_from(User)
    if status_filter:
        count_query = count_query.where(User.status == status_filter)
    total = (await session.execute(count_query)).scalar() or 0

    # Data query
    query = select(User).order_by(User.created_at.desc())
    if status_filter:
        query = query.where(User.status == status_filter)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/me", response_model=UserWithRolesResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserWithRolesResponse:
    """Get current user's profile."""
    from sdlc_agent.api.schemas.rbac import RoleResponse

    roles = [RoleResponse.model_validate(ur.role) for ur in current_user.user_roles]
    response = UserWithRolesResponse.model_validate(current_user)
    response.roles = roles
    return response


@router.get("/{user_id}", response_model=UserWithRolesResponse)
async def get_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:read:any"))],
) -> UserWithRolesResponse:
    """Get a specific user by ID."""
    from sdlc_agent.api.schemas.rbac import RoleResponse

    query = select(User).where(User.id == user_id).options(
        selectinload(User.user_roles).selectinload(UserRole.role)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise EntityNotFoundError("User", str(user_id))

    roles = [RoleResponse.model_validate(ur.role) for ur in user.user_roles]
    response = UserWithRolesResponse.model_validate(user)
    response.roles = roles
    return response


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: uuid.UUID,
    user_data: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:update:any"))],
) -> UserResponse:
    """Update a user."""
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise EntityNotFoundError("User", str(user_id))

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # Log audit
    audit = RBACAuditLog(
        action=AuditAction.USER_UPDATED,
        resource_type="user",
        resource_id=str(user.id),
        details={"updated_fields": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(user)

    logger.info(f"Updated user {user.username}")
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:delete:any"))],
) -> None:
    """Delete a user."""
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise EntityNotFoundError("User", str(user_id))

    # Log audit before deletion
    audit = RBACAuditLog(
        action=AuditAction.USER_DELETED,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.delete(user)
    await session.commit()

    logger.info(f"Deleted user {user.username}")


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: Request,
    password_data: UserPasswordUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Change current user's password."""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    current_user.password_hash = hash_password(password_data.new_password)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PASSWORD_CHANGED,
        resource_type="user",
        resource_id=str(current_user.id),
        details={},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    logger.info(f"User {current_user.username} changed their password")


# =============================================================================
# User-Role Assignments
# =============================================================================


@router.get("/{user_id}/roles", response_model=list[UserRoleResponse])
async def get_user_roles(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("users:read:any"))],
) -> list[UserRoleResponse]:
    """Get roles assigned to a user."""
    query = select(UserRole).where(UserRole.user_id == user_id).options(
        selectinload(UserRole.role)
    )
    result = await session.execute(query)
    user_roles = result.scalars().all()

    return [
        UserRoleResponse(
            user_id=ur.user_id,
            role_id=ur.role_id,
            role_name=ur.role.name,
            assigned_by=ur.assigned_by,
            expires_at=ur.expires_at,
            created_at=ur.created_at,
        )
        for ur in user_roles
    ]


@router.post("/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    request: Request,
    user_id: uuid.UUID,
    role_data: UserRoleAssign,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("users:update:any"))],
) -> UserRoleResponse:
    """Assign a role to a user."""
    # Verify user exists
    user = await session.get(User, user_id)
    if not user:
        raise EntityNotFoundError("User", str(user_id))

    # Verify role exists
    role = await session.get(Role, role_data.role_id)
    if not role:
        raise EntityNotFoundError("Role", str(role_data.role_id))

    # Check if already assigned
    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_data.role_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AuthorizationError("Role already assigned to user")

    # Create assignment
    user_role = UserRole(
        user_id=user_id,
        role_id=role_data.role_id,
        assigned_by=current_user.email,
        expires_at=role_data.expires_at,
    )
    session.add(user_role)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.ROLE_ASSIGNED,
        resource_type="user_role",
        resource_id=f"{user_id}:{role_data.role_id}",
        details={"user_id": str(user_id), "role_id": str(role_data.role_id), "role_name": role.name},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(user_role)

    logger.info(f"Assigned role {role.name} to user {user.username}")

    return UserRoleResponse(
        user_id=user_role.user_id,
        role_id=user_role.role_id,
        role_name=role.name,
        assigned_by=user_role.assigned_by,
        expires_at=user_role.expires_at,
        created_at=user_role.created_at,
    )


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role_from_user(
    request: Request,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("users:update:any"))],
) -> None:
    """Revoke a role from a user."""
    query = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id,
    ).options(selectinload(UserRole.role))
    result = await session.execute(query)
    user_role = result.scalar_one_or_none()

    if not user_role:
        raise EntityNotFoundError("UserRole", f"{user_id}:{role_id}")

    role_name = user_role.role.name

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.ROLE_REVOKED,
        resource_type="user_role",
        resource_id=f"{user_id}:{role_id}",
        details={"user_id": str(user_id), "role_id": str(role_id), "role_name": role_name},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.delete(user_role)
    await session.commit()

    logger.info(f"Revoked role {role_name} from user {user_id}")
