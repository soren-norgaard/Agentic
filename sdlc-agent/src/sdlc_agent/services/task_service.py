# =============================================================================
# SDLC Agent - Task Persistence Service
# =============================================================================
"""
Service for persisting tasks (epics, stories, tasks) to the database.
Used by agents to store their outputs.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Task, TaskType, TaskStatus, TaskPriority, get_session_context

logger = get_logger(__name__)


class TaskService:
    """Service for managing tasks in the database."""

    @staticmethod
    async def create_epic(
        project_id: uuid.UUID,
        title: str,
        description: str | None = None,
        business_value: str | None = None,
        workflow_id: uuid.UUID | None = None,
    ) -> Task:
        """Create an epic in the database."""
        async with get_session_context() as session:
            task = Task(
                project_id=project_id,
                title=title,
                description=description,
                task_type=TaskType.EPIC,
                status=TaskStatus.BACKLOG,
                priority=TaskPriority.HIGH,
                technical_notes=business_value,
                labels=["workflow-generated"] if workflow_id else [],
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            
            logger.info(
                "Epic created",
                epic_id=str(task.id),
                title=title,
                project_id=str(project_id),
            )
            return task

    @staticmethod
    async def create_story(
        project_id: uuid.UUID,
        title: str,
        description: str | None = None,
        parent_id: uuid.UUID | None = None,
        acceptance_criteria: list[dict[str, Any]] | None = None,
        story_points: int | None = None,
        as_a: str | None = None,
        i_want: str | None = None,
        so_that: str | None = None,
        workflow_id: uuid.UUID | None = None,
    ) -> Task:
        """Create a user story in the database."""
        # Build description from user story format if provided
        if as_a and i_want and so_that:
            full_description = f"As a {as_a}, I want {i_want}, so that {so_that}"
            if description:
                full_description += f"\n\n{description}"
            description = full_description

        async with get_session_context() as session:
            task = Task(
                project_id=project_id,
                parent_id=parent_id,
                title=title,
                description=description,
                task_type=TaskType.STORY,
                status=TaskStatus.BACKLOG,
                priority=TaskPriority.MEDIUM,
                acceptance_criteria=acceptance_criteria or [],
                story_points=story_points,
                labels=["workflow-generated"] if workflow_id else [],
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            
            logger.info(
                "Story created",
                story_id=str(task.id),
                title=title,
                project_id=str(project_id),
            )
            return task

    @staticmethod
    async def create_task(
        project_id: uuid.UUID,
        title: str,
        description: str | None = None,
        parent_id: uuid.UUID | None = None,
        task_type: str = "task",
        story_points: int | None = None,
        estimated_hours: float | None = None,
        priority: str = "medium",
        skills_required: list[str] | None = None,
        workflow_id: uuid.UUID | None = None,
    ) -> Task:
        """Create a task in the database."""
        # Map string priority to enum
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.MEDIUM)

        # Map task type
        type_map = {
            "task": TaskType.TASK,
            "feature": TaskType.TASK,
            "bug": TaskType.BUG,
            "spike": TaskType.SPIKE,
        }
        db_task_type = type_map.get(task_type.lower(), TaskType.TASK)

        labels = ["workflow-generated"] if workflow_id else []
        if skills_required:
            labels.extend([f"skill:{s}" for s in skills_required[:5]])

        async with get_session_context() as session:
            task = Task(
                project_id=project_id,
                parent_id=parent_id,
                title=title,
                description=description,
                task_type=db_task_type,
                status=TaskStatus.BACKLOG,
                priority=task_priority,
                story_points=story_points,
                estimated_hours=estimated_hours,
                labels=labels,
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            
            logger.info(
                "Task created",
                task_id=str(task.id),
                title=title,
                project_id=str(project_id),
            )
            return task

    @staticmethod
    async def update_task_status(
        task_id: uuid.UUID,
        status: TaskStatus,
    ) -> Task | None:
        """Update a task's status."""
        async with get_session_context() as session:
            task = await session.get(Task, task_id)
            if task:
                task.status = status
                await session.flush()
                await session.refresh(task)
                logger.info(
                    "Task status updated",
                    task_id=str(task_id),
                    new_status=status.value,
                )
            return task

    @staticmethod
    async def get_project_tasks(
        project_id: uuid.UUID,
        task_type: TaskType | None = None,
    ) -> list[Task]:
        """Get all tasks for a project."""
        from sqlalchemy import select
        
        async with get_session_context() as session:
            query = select(Task).where(Task.project_id == project_id)
            if task_type:
                query = query.where(Task.task_type == task_type)
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def find_epic_by_title(
        project_id: uuid.UUID,
        title: str,
    ) -> Task | None:
        """Find an epic by title (for linking stories)."""
        from sqlalchemy import select, and_
        
        async with get_session_context() as session:
            query = select(Task).where(
                and_(
                    Task.project_id == project_id,
                    Task.task_type == TaskType.EPIC,
                    Task.title.ilike(f"%{title}%"),
                )
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()
