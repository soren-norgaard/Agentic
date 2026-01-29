# =============================================================================
# SDLC Agent - Workflow Routes
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
from sdlc_agent.db import Project, Workflow, WorkflowStatus, get_session

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    project_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    initial_state: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    status: WorkflowStatus
    current_state: dict[str, Any]
    started_at: str | None
    completed_at: str | None
    error_message: str | None
    retry_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Schema for paginated workflow list."""

    items: list[WorkflowResponse]
    total: int
    page: int
    page_size: int
    pages: int


class WorkflowActionRequest(BaseModel):
    """Schema for workflow actions (start, pause, resume, cancel)."""

    action: str = Field(..., pattern="^(start|pause|resume|cancel)$")


class HumanInputRequest(BaseModel):
    """Schema for submitting human input."""

    input_id: uuid.UUID
    response: dict[str, Any]


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    """
    Create a new workflow.

    Args:
        data: Workflow creation data
        session: Database session

    Returns:
        Created workflow
    """
    # Verify project exists
    project = await session.get(Project, data.project_id)
    if not project:
        raise EntityNotFoundError("Project", str(data.project_id))

    workflow = Workflow(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        current_state=data.initial_state,
    )
    session.add(workflow)
    await session.flush()
    await session.refresh(workflow)

    logger.info(
        "Workflow created",
        workflow_id=str(workflow.id),
        project_id=str(data.project_id),
        name=workflow.name,
    )
    return workflow


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: WorkflowStatus | None = Query(None, alias="status"),
) -> dict[str, Any]:
    """
    List workflows with pagination.

    Args:
        session: Database session
        project_id: Optional project filter
        page: Page number
        page_size: Items per page
        status_filter: Optional status filter

    Returns:
        Paginated list of workflows
    """
    query = select(Workflow)
    count_query = select(func.count(Workflow.id))

    if project_id:
        query = query.where(Workflow.project_id == project_id)
        count_query = count_query.where(Workflow.project_id == project_id)

    if status_filter:
        query = query.where(Workflow.status == status_filter)
        count_query = count_query.where(Workflow.status == status_filter)

    total = await session.scalar(count_query) or 0

    offset = (page - 1) * page_size
    query = query.order_by(Workflow.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    workflows = list(result.scalars().all())

    return {
        "items": workflows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    """
    Get a workflow by ID.

    Args:
        workflow_id: Workflow UUID
        session: Database session

    Returns:
        Workflow details
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))
    return workflow


@router.post("/{workflow_id}/actions", response_model=WorkflowResponse)
async def workflow_action(
    workflow_id: uuid.UUID,
    data: WorkflowActionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    """
    Perform an action on a workflow (start, pause, resume, cancel).

    Args:
        workflow_id: Workflow UUID
        data: Action request
        session: Database session

    Returns:
        Updated workflow
    """
    from datetime import UTC, datetime

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    action = data.action

    if action == "start":
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Cannot start workflow in {workflow.status} status")
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(UTC)
        # TODO: Trigger agent execution

    elif action == "pause":
        if workflow.status != WorkflowStatus.RUNNING:
            raise ValueError(f"Cannot pause workflow in {workflow.status} status")
        workflow.status = WorkflowStatus.PAUSED

    elif action == "resume":
        if workflow.status != WorkflowStatus.PAUSED:
            raise ValueError(f"Cannot resume workflow in {workflow.status} status")
        workflow.status = WorkflowStatus.RUNNING
        # TODO: Resume agent execution

    elif action == "cancel":
        if workflow.status in {WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED}:
            raise ValueError(f"Cannot cancel workflow in {workflow.status} status")
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now(UTC)

    await session.flush()
    await session.refresh(workflow)

    logger.info(
        "Workflow action performed",
        workflow_id=str(workflow_id),
        action=action,
        new_status=workflow.status.value,
    )
    return workflow


@router.post("/{workflow_id}/input", response_model=WorkflowResponse)
async def submit_human_input(
    workflow_id: uuid.UUID,
    data: HumanInputRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    """
    Submit human input for a workflow awaiting input.

    Args:
        workflow_id: Workflow UUID
        data: Human input data
        session: Database session

    Returns:
        Updated workflow
    """
    from datetime import UTC, datetime

    from sdlc_agent.db import HumanInput

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    if workflow.status != WorkflowStatus.AWAITING_INPUT:
        raise ValueError("Workflow is not awaiting input")

    # Find and update the human input record
    human_input = await session.get(HumanInput, data.input_id)
    if not human_input or human_input.workflow_id != workflow_id:
        raise EntityNotFoundError("HumanInput", str(data.input_id))

    human_input.response = data.response
    human_input.responded_at = datetime.now(UTC)
    human_input.is_resolved = True

    # Resume workflow
    workflow.status = WorkflowStatus.RUNNING

    await session.flush()
    await session.refresh(workflow)

    logger.info(
        "Human input submitted",
        workflow_id=str(workflow_id),
        input_id=str(data.input_id),
    )
    return workflow
