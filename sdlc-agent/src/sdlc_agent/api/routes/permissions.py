# =============================================================================
# SDLC Agent - Permission Management Routes
# =============================================================================

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.api.routes.rbac_deps import get_current_user, require_permission
from sdlc_agent.api.schemas.rbac import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
)
from sdlc_agent.core.exceptions import AuthorizationError, EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import (
    AuditAction,
    Permission,
    RBACAuditLog,
    User,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Permission CRUD
# =============================================================================


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    request: Request,
    permission_data: PermissionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("permissions:create:any"))],
) -> PermissionResponse:
    """Create a new permission."""
    # Check for existing permission
    existing = await session.execute(
        select(Permission).where(Permission.code == permission_data.code)
    )
    if existing.scalar_one_or_none():
        raise AuthorizationError("Permission with this code already exists")

    # Create permission
    permission = Permission(
        code=permission_data.code,
        name=permission_data.name,
        description=permission_data.description,
        resource=permission_data.resource,
        action=permission_data.action,
        scope=permission_data.scope,
    )
    session.add(permission)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PERMISSION_CREATED,
        resource_type="permission",
        resource_id=str(permission.id),
        details={"code": permission.code},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(permission)

    logger.info(f"Created permission {permission.code}")
    return PermissionResponse.model_validate(permission)


@router.get("", response_model=PermissionListResponse)
async def list_permissions(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("permissions:read:any"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    resource: str | None = Query(None),
) -> PermissionListResponse:
    """List all permissions with pagination."""
    # Count query
    count_query = select(func.count()).select_from(Permission)
    if resource:
        count_query = count_query.where(Permission.resource == resource)
    total = (await session.execute(count_query)).scalar() or 0

    # Data query
    query = select(Permission).order_by(Permission.resource, Permission.action)
    if resource:
        query = query.where(Permission.resource == resource)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    permissions = result.scalars().all()

    return PermissionListResponse(
        items=[PermissionResponse.model_validate(p) for p in permissions],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/resources", response_model=list[str])
async def list_permission_resources(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("permissions:read:any"))],
) -> list[str]:
    """List all unique resource types in permissions."""
    query = select(Permission.resource).distinct().order_by(Permission.resource)
    result = await session.execute(query)
    return [r[0] for r in result.all()]


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("permissions:read:any"))],
) -> PermissionResponse:
    """Get a specific permission by ID."""
    permission = await session.get(Permission, permission_id)

    if not permission:
        raise EntityNotFoundError("Permission", str(permission_id))

    return PermissionResponse.model_validate(permission)


@router.patch("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    request: Request,
    permission_id: uuid.UUID,
    permission_data: PermissionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("permissions:update:any"))],
) -> PermissionResponse:
    """Update a permission (name and description only)."""
    permission = await session.get(Permission, permission_id)

    if not permission:
        raise EntityNotFoundError("Permission", str(permission_id))

    # Update fields
    update_data = permission_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PERMISSION_UPDATED,
        resource_type="permission",
        resource_id=str(permission.id),
        details={"updated_fields": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.commit()
    await session.refresh(permission)

    logger.info(f"Updated permission {permission.code}")
    return PermissionResponse.model_validate(permission)


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    request: Request,
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("permissions:delete:any"))],
) -> None:
    """Delete a permission."""
    permission = await session.get(Permission, permission_id)

    if not permission:
        raise EntityNotFoundError("Permission", str(permission_id))

    # Log audit
    audit = RBACAuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=AuditAction.PERMISSION_DELETED,
        resource_type="permission",
        resource_id=str(permission.id),
        details={"code": permission.code},
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)

    await session.delete(permission)
    await session.commit()

    logger.info(f"Deleted permission {permission.code}")
