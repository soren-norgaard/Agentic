# =============================================================================
# SDLC Agent - Role Management Routes
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
    PermissionResponse,
    RoleCreate,
    RoleListResponse,
    RolePermissionAssign,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
    RoleWithPermissionsResponse,
)
from sdlc_agent.core.exceptions import AuthorizationError, EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import (
    AuditAction,
    Permission,
    RBACAuditLog,
    Role,
    RolePermission,
    RoleType,
    User,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Role CRUD
# =============================================================================


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: Request,
    role_data: RoleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("roles:create:any"))],
) -> RoleResponse:
    """Create a new role."""
    # Check for existing role
    existing = await session.execute(
        select(Role).where(Role.name == role_data.name)
    )
    if existing.scalar_one_or_none():
        raise AuthorizationError("Role with this name already exists")

    # Create role
    role = Role(
        name=role_data.name,
        description=role_data.description,
        priority=role_data.priority,
        role_type=RoleType.CUSTOM,
        is_active=True,
    )
    session.add(role)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.ROLE_CREATED,
        resource_type="role",
        resource_id=str(role.id),
        details={"name": role.name},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(role)

    logger.info(f"Created role {role.name}")
    return RoleResponse.model_validate(role)


@router.get("", response_model=RoleListResponse)
async def list_roles(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("roles:read:any"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
) -> RoleListResponse:
    """List all roles with pagination."""
    # Count query
    count_query = select(func.count()).select_from(Role)
    if active_only:
        count_query = count_query.where(Role.is_active == True)
    total = (await session.execute(count_query)).scalar() or 0

    # Data query
    query = select(Role).order_by(Role.priority.desc(), Role.name)
    if active_only:
        query = query.where(Role.is_active == True)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    roles = result.scalars().all()

    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{role_id}", response_model=RoleWithPermissionsResponse)
async def get_role(
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("roles:read:any"))],
) -> RoleWithPermissionsResponse:
    """Get a specific role by ID with its permissions."""
    query = select(Role).where(Role.id == role_id).options(
        selectinload(Role.role_permissions).selectinload(RolePermission.permission)
    )
    result = await session.execute(query)
    role = result.scalar_one_or_none()

    if not role:
        raise EntityNotFoundError("Role", str(role_id))

    permissions = [
        PermissionResponse.model_validate(rp.permission)
        for rp in role.role_permissions
    ]
    response = RoleWithPermissionsResponse.model_validate(role)
    response.permissions = permissions
    return response


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    request: Request,
    role_id: uuid.UUID,
    role_data: RoleUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("roles:update:any"))],
) -> RoleResponse:
    """Update a role."""
    query = select(Role).where(Role.id == role_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()

    if not role:
        raise EntityNotFoundError("Role", str(role_id))

    # Cannot modify system roles name
    if role.role_type == RoleType.SYSTEM and role_data.name:
        raise AuthorizationError("Cannot change name of system role")

    # Update fields
    update_data = role_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.ROLE_UPDATED,
        resource_type="role",
        resource_id=str(role.id),
        details={"updated_fields": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(role)

    logger.info(f"Updated role {role.name}")
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    request: Request,
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("roles:delete:any"))],
) -> None:
    """Delete a role."""
    query = select(Role).where(Role.id == role_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()

    if not role:
        raise EntityNotFoundError("Role", str(role_id))

    # Cannot delete system roles
    if role.role_type == RoleType.SYSTEM:
        raise AuthorizationError("Cannot delete system role")

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.ROLE_DELETED,
        resource_type="role",
        resource_id=str(role.id),
        details={"name": role.name},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.delete(role)
    await session.commit()

    logger.info(f"Deleted role {role.name}")


# =============================================================================
# Role-Permission Assignments
# =============================================================================


@router.get("/{role_id}/permissions", response_model=list[RolePermissionResponse])
async def get_role_permissions(
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("roles:read:any"))],
) -> list[RolePermissionResponse]:
    """Get permissions assigned to a role."""
    query = select(RolePermission).where(RolePermission.role_id == role_id).options(
        selectinload(RolePermission.permission)
    )
    result = await session.execute(query)
    role_permissions = result.scalars().all()

    return [
        RolePermissionResponse(
            role_id=rp.role_id,
            permission_id=rp.permission_id,
            permission_code=rp.permission.code,
            granted_by=rp.granted_by,
            created_at=rp.created_at,
        )
        for rp in role_permissions
    ]


@router.post("/{role_id}/permissions", response_model=RolePermissionResponse, status_code=status.HTTP_201_CREATED)
async def grant_permission_to_role(
    request: Request,
    role_id: uuid.UUID,
    permission_data: RolePermissionAssign,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("roles:update:any"))],
) -> RolePermissionResponse:
    """Grant a permission to a role."""
    # Verify role exists
    role = await session.get(Role, role_id)
    if not role:
        raise EntityNotFoundError("Role", str(role_id))

    # Verify permission exists
    permission = await session.get(Permission, permission_data.permission_id)
    if not permission:
        raise EntityNotFoundError("Permission", str(permission_data.permission_id))

    # Check if already granted
    existing = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_data.permission_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AuthorizationError("Permission already granted to role")

    # Create grant
    role_permission = RolePermission(
        role_id=role_id,
        permission_id=permission_data.permission_id,
        granted_by=current_user.email,
    )
    session.add(role_permission)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PERMISSION_GRANTED,
        resource_type="role_permission",
        resource_id=f"{role_id}:{permission_data.permission_id}",
        details={"role_name": role.name, "permission_code": permission.code},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(role_permission)

    logger.info(f"Granted permission {permission.code} to role {role.name}")

    return RolePermissionResponse(
        role_id=role_permission.role_id,
        permission_id=role_permission.permission_id,
        permission_code=permission.code,
        granted_by=role_permission.granted_by,
        created_at=role_permission.created_at,
    )


@router.delete("/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission_from_role(
    request: Request,
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("roles:update:any"))],
) -> None:
    """Revoke a permission from a role."""
    query = select(RolePermission).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id,
    ).options(selectinload(RolePermission.permission), selectinload(RolePermission.role))
    result = await session.execute(query)
    role_permission = result.scalar_one_or_none()

    if not role_permission:
        raise EntityNotFoundError("RolePermission", f"{role_id}:{permission_id}")

    role_name = role_permission.role.name
    permission_code = role_permission.permission.code

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PERMISSION_REVOKED,
        resource_type="role_permission",
        resource_id=f"{role_id}:{permission_id}",
        details={"role_name": role_name, "permission_code": permission_code},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.delete(role_permission)
    await session.commit()

    logger.info(f"Revoked permission {permission_code} from role {role_name}")
