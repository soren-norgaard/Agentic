# =============================================================================
# SDLC Agent - Task Routes (Epics, Stories, Tasks)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sdlc_agent.core.exceptions import EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Task, TaskStatus, TaskType, TaskPriority, get_session

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    project_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    task_type: TaskType = TaskType.TASK
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    story_points: int | None = None
    estimated_hours: float | None = None
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)
    technical_notes: str | None = None
    labels: list[str] = Field(default_factory=list)
    workflow_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    story_points: int | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None
    acceptance_criteria: list[dict[str, Any]] | None = None
    technical_notes: str | None = None
    labels: list[str] | None = None


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    title: str
    description: str | None
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    story_points: int | None
    estimated_hours: float | None
    actual_hours: float | None
    acceptance_criteria: list[Any]  # Can be strings or dicts
    technical_notes: str | None
    labels: list[str]
    external_id: str | None
    children_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


class TaskWithChildren(TaskResponse):
    """Task with nested children."""
    children: list["TaskWithChildren"] = []


class TaskListResponse(BaseModel):
    """Schema for paginated task list."""

    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskStats(BaseModel):
    """Statistics about tasks."""
    
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_priority: dict[str, int]
    total_story_points: int
    completed_story_points: int


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Task:
    """Create a new task, epic, or story."""
    task = Task(
        project_id=data.project_id,
        parent_id=data.parent_id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        status=data.status,
        priority=data.priority,
        story_points=data.story_points,
        estimated_hours=data.estimated_hours,
        acceptance_criteria=data.acceptance_criteria,
        technical_notes=data.technical_notes,
        labels=data.labels,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)

    logger.info(
        "Task created",
        task_id=str(task.id),
        task_type=data.task_type.value,
        title=task.title,
    )
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    task_type: TaskType | None = None,
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """List tasks with filtering and pagination."""
    query = select(Task)
    count_query = select(func.count(Task.id))

    filters = []
    if project_id:
        filters.append(Task.project_id == project_id)
    if parent_id:
        filters.append(Task.parent_id == parent_id)
    elif parent_id is None and task_type == TaskType.EPIC:
        # Get only root-level epics
        filters.append(Task.parent_id.is_(None))
    if task_type:
        filters.append(Task.task_type == task_type)
    if status_filter:
        filters.append(Task.status == status_filter)
    if priority:
        filters.append(Task.priority == priority)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    query = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    tasks = result.scalars().all()

    return {
        "items": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/hierarchy/{project_id}", response_model=list[TaskWithChildren])
async def get_task_hierarchy(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, Any]]:
    """Get the full task hierarchy for a project (epics -> stories -> tasks).
    
    If tasks don't have parent_id set, builds a logical hierarchy based on task type.
    """
    # Get all tasks for the project
    query = select(Task).where(Task.project_id == project_id).order_by(Task.created_at)
    result = await session.execute(query)
    all_tasks = list(result.scalars().all())

    # Check if we have real parent relationships
    has_real_hierarchy = any(t.parent_id is not None for t in all_tasks)
    
    if has_real_hierarchy:
        # Build hierarchy from parent_id relationships
        task_map = {t.id: t for t in all_tasks}
        
        def build_tree(task: Task) -> dict[str, Any]:
            children = [t for t in all_tasks if t.parent_id == task.id]
            return {
                **TaskResponse.model_validate(task).model_dump(),
                "children": [build_tree(child) for child in children],
                "children_count": len(children),
            }
        
        root_tasks = [t for t in all_tasks if t.parent_id is None]
        return [build_tree(t) for t in root_tasks]
    
    else:
        # Build logical hierarchy based on task type: epics -> stories -> tasks
        epics = [t for t in all_tasks if t.task_type == TaskType.EPIC]
        stories = [t for t in all_tasks if t.task_type == TaskType.STORY]
        tasks = [t for t in all_tasks if t.task_type == TaskType.TASK]
        bugs = [t for t in all_tasks if t.task_type == TaskType.BUG]
        spikes = [t for t in all_tasks if t.task_type == TaskType.SPIKE]
        
        # If we have epics, put stories under them (distribute evenly)
        if epics:
            result_hierarchy = []
            stories_per_epic = max(1, len(stories) // len(epics)) if stories else 0
            tasks_per_story = max(1, len(tasks) // max(len(stories), 1)) if tasks else 0
            
            story_idx = 0
            task_idx = 0
            
            for epic in epics:
                epic_data = TaskResponse.model_validate(epic).model_dump()
                epic_children = []
                
                # Assign stories to this epic
                epic_stories = stories[story_idx:story_idx + stories_per_epic]
                story_idx += stories_per_epic
                
                for story in epic_stories:
                    story_data = TaskResponse.model_validate(story).model_dump()
                    story_children = []
                    
                    # Assign tasks to this story
                    story_tasks = tasks[task_idx:task_idx + tasks_per_story]
                    task_idx += tasks_per_story
                    
                    for task in story_tasks:
                        task_data = TaskResponse.model_validate(task).model_dump()
                        task_data["children"] = []
                        task_data["children_count"] = 0
                        story_children.append(task_data)
                    
                    story_data["children"] = story_children
                    story_data["children_count"] = len(story_children)
                    epic_children.append(story_data)
                
                epic_data["children"] = epic_children
                epic_data["children_count"] = len(epic_children)
                result_hierarchy.append(epic_data)
            
            # Add remaining items
            for story in stories[story_idx:]:
                story_data = TaskResponse.model_validate(story).model_dump()
                story_data["children"] = []
                story_data["children_count"] = 0
                result_hierarchy.append(story_data)
            
            for task in tasks[task_idx:]:
                task_data = TaskResponse.model_validate(task).model_dump()
                task_data["children"] = []
                task_data["children_count"] = 0
                result_hierarchy.append(task_data)
            
            # Add bugs and spikes at root level
            for item in bugs + spikes:
                item_data = TaskResponse.model_validate(item).model_dump()
                item_data["children"] = []
                item_data["children_count"] = 0
                result_hierarchy.append(item_data)
            
            return result_hierarchy
        
        else:
            # No epics - just return flat list
            hierarchy = []
            for t in all_tasks:
                t_data = TaskResponse.model_validate(t).model_dump()
                t_data["children"] = []
                t_data["children_count"] = 0
                hierarchy.append(t_data)
            return hierarchy


@router.get("/stats/{project_id}", response_model=TaskStats)
async def get_task_stats(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Get task statistics for a project."""
    query = select(Task).where(Task.project_id == project_id)
    result = await session.execute(query)
    tasks = result.scalars().all()

    by_status = {}
    by_type = {}
    by_priority = {}
    total_points = 0
    completed_points = 0

    for task in tasks:
        by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
        by_type[task.task_type.value] = by_type.get(task.task_type.value, 0) + 1
        by_priority[task.priority.value] = by_priority.get(task.priority.value, 0) + 1
        
        if task.story_points:
            total_points += task.story_points
            if task.status == TaskStatus.DONE:
                completed_points += task.story_points

    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_type": by_type,
        "by_priority": by_priority,
        "total_story_points": total_points,
        "completed_story_points": completed_points,
    }


@router.get("/{task_id}", response_model=TaskWithChildren)
async def get_task(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Get a single task with its children."""
    query = select(Task).where(Task.id == task_id).options(
        selectinload(Task.children)
    )
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    def build_tree(t: Task) -> dict[str, Any]:
        return {
            **TaskResponse.model_validate(t).model_dump(),
            "children": [build_tree(child) for child in t.children],
            "children_count": len(t.children),
        }

    return build_tree(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Task:
    """Update a task."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await session.flush()
    await session.refresh(task)

    logger.info("Task updated", task_id=str(task_id))
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a task and its children."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    logger.info("Task deleted", task_id=str(task_id))


@router.post("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: uuid.UUID,
    new_status: TaskStatus,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Task:
    """Move a task to a different status (for Kanban boards)."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status
    task.status = new_status
    await session.flush()
    await session.refresh(task)

    logger.info(
        "Task moved",
        task_id=str(task_id),
        from_status=old_status.value,
        to_status=new_status.value,
    )
    return task
