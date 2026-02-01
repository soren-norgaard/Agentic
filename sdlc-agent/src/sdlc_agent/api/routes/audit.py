# =============================================================================
# SDLC Agent - Audit Log Routes
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from sdlc_agent.api.routes.rbac_deps import require_permission
from sdlc_agent.api.schemas.rbac import (
    AuditLogListResponse,
    AuditLogResponse,
)
from sdlc_agent.core.exceptions import EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import AuditAction, RBACAuditLog

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("audit:read:any"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    actor_id: uuid.UUID | None = Query(None),
    action: AuditAction | None = Query(None),
    resource_type: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> AuditLogListResponse:
    """List audit logs with filtering and pagination.

    Audit logs are read-only and cannot be modified or deleted.
    """
    # Build filters
    filters = []
    if actor_id:
        filters.append(RBACAuditLog.actor_id == actor_id)
    if action:
        filters.append(RBACAuditLog.action == action)
    if resource_type:
        filters.append(RBACAuditLog.resource_type == resource_type)
    if from_date:
        filters.append(RBACAuditLog.timestamp >= from_date)
    if to_date:
        filters.append(RBACAuditLog.timestamp <= to_date)

    # Count query
    count_query = select(func.count()).select_from(RBACAuditLog)
    if filters:
        count_query = count_query.where(and_(*filters))
    total = (await session.execute(count_query)).scalar() or 0

    # Data query
    query = select(RBACAuditLog).order_by(RBACAuditLog.timestamp.desc())
    if filters:
        query = query.where(and_(*filters))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/actions", response_model=list[str])
async def list_audit_actions(
    _: Annotated[None, Depends(require_permission("audit:read:any"))],
) -> list[str]:
    """List all available audit action types."""
    return [action.value for action in AuditAction]


@router.get("/resources", response_model=list[str])
async def list_audit_resource_types(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("audit:read:any"))],
) -> list[str]:
    """List all unique resource types in audit logs."""
    query = select(RBACAuditLog.resource_type).distinct().order_by(RBACAuditLog.resource_type)
    result = await session.execute(query)
    return [r[0] for r in result.all()]


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("audit:read:any"))],
) -> AuditLogResponse:
    """Get a specific audit log entry by ID."""
    log = await session.get(RBACAuditLog, log_id)

    if not log:
        raise EntityNotFoundError("AuditLog", str(log_id))

    return AuditLogResponse.model_validate(log)


@router.get("/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(require_permission("audit:read:any"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> AuditLogListResponse:
    """Get all audit logs for a specific user (as actor)."""
    # Count query
    count_query = select(func.count()).select_from(RBACAuditLog).where(
        RBACAuditLog.actor_id == user_id
    )
    total = (await session.execute(count_query)).scalar() or 0

    # Data query
    query = (
        select(RBACAuditLog)
        .where(RBACAuditLog.actor_id == user_id)
        .order_by(RBACAuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )
