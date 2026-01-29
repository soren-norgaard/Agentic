# =============================================================================
# SDLC Agent - Project Routes
# =============================================================================

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.exceptions import EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Project, ProjectStatus, get_session

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    repository_url: str | None = Field(None, max_length=500)
    repository_branch: str = Field("main", max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    status: ProjectStatus | None = None
    repository_url: str | None = Field(None, max_length=500)
    repository_branch: str | None = Field(None, max_length=255)
    config: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    repository_url: str | None
    repository_branch: str
    config: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""

    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    """
    Create a new project.

    Args:
        data: Project creation data
        session: Database session

    Returns:
        Created project
    """
    project = Project(
        name=data.name,
        description=data.description,
        repository_url=data.repository_url,
        repository_branch=data.repository_branch,
        config=data.config,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)

    logger.info("Project created", project_id=str(project.id), name=project.name)
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ProjectStatus | None = Query(None, alias="status"),
) -> dict[str, Any]:
    """
    List all projects with pagination.

    Args:
        session: Database session
        page: Page number
        page_size: Items per page
        status_filter: Optional status filter

    Returns:
        Paginated list of projects
    """
    # Base query
    query = select(Project)
    count_query = select(func.count(Project.id))

    # Apply filters
    if status_filter:
        query = query.where(Project.status == status_filter)
        count_query = count_query.where(Project.status == status_filter)

    # Get total count
    total = await session.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    projects = list(result.scalars().all())

    return {
        "items": projects,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    """
    Get a project by ID.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Project details

    Raises:
        EntityNotFoundError: If project not found
    """
    project = await session.get(Project, project_id)
    if not project:
        raise EntityNotFoundError("Project", str(project_id))
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    """
    Update a project.

    Args:
        project_id: Project UUID
        data: Update data
        session: Database session

    Returns:
        Updated project

    Raises:
        EntityNotFoundError: If project not found
    """
    project = await session.get(Project, project_id)
    if not project:
        raise EntityNotFoundError("Project", str(project_id))

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await session.flush()
    await session.refresh(project)

    logger.info("Project updated", project_id=str(project_id))
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a project.

    Args:
        project_id: Project UUID
        session: Database session

    Raises:
        EntityNotFoundError: If project not found
    """
    project = await session.get(Project, project_id)
    if not project:
        raise EntityNotFoundError("Project", str(project_id))

    await session.delete(project)
    logger.info("Project deleted", project_id=str(project_id))
