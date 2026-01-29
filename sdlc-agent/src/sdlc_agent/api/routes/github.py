# =============================================================================
# SDLC Agent - GitHub Integration Routes
# =============================================================================

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Task, TaskType, TaskStatus, TaskPriority, get_session
from sdlc_agent.services.github_service import (
    GitHubService,
    GitHubIssue,
    GitHubLabel,
    get_github_service,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class GitHubConfigResponse(BaseModel):
    """GitHub configuration status."""
    configured: bool
    owner: str | None
    repo: str | None
    auto_sync_enabled: bool


class GitHubConfigUpdate(BaseModel):
    """Update GitHub configuration."""
    token: str | None = None
    owner: str | None = None
    repo: str | None = None
    auto_sync_enabled: bool | None = None


class SyncTaskRequest(BaseModel):
    """Request to sync a task to GitHub."""
    task_id: uuid.UUID


class SyncTaskResponse(BaseModel):
    """Response after syncing a task to GitHub."""
    task_id: uuid.UUID
    github_issue_number: int
    github_issue_url: str
    synced: bool


class SyncAllResponse(BaseModel):
    """Response after syncing all tasks."""
    synced_count: int
    failed_count: int
    details: list[dict[str, Any]]


class GitHubIssueResponse(BaseModel):
    """GitHub Issue response."""
    number: int
    title: str
    state: str
    labels: list[str]
    html_url: str


class ImportIssueRequest(BaseModel):
    """Request to import a GitHub issue as a task."""
    issue_number: int
    project_id: uuid.UUID
    task_type: str = "task"


# =============================================================================
# Routes
# =============================================================================


@router.get("/config", response_model=GitHubConfigResponse)
async def get_github_config() -> dict[str, Any]:
    """Get current GitHub configuration status."""
    settings = get_settings()
    return {
        "configured": settings.github.is_configured,
        "owner": settings.github.owner or None,
        "repo": settings.github.repo or None,
        "auto_sync_enabled": settings.github.auto_sync_enabled,
    }


@router.post("/setup-labels")
async def setup_github_labels() -> dict[str, Any]:
    """
    Set up SDLC labels in the GitHub repository.
    
    Creates labels like: epic, story, task, needs-design, ready-for-dev, etc.
    """
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured. Set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value() if settings.github.token else None,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        created = await github.ensure_labels_exist()
        await github.close()
        
        return {
            "success": True,
            "labels_created": len(created),
            "message": f"Created {len(created)} new labels",
        }
    except Exception as e:
        logger.exception("Failed to setup GitHub labels", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup labels: {str(e)}",
        )


@router.post("/sync-task", response_model=SyncTaskResponse)
async def sync_task_to_github(
    request: SyncTaskRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Sync a single task to GitHub as an issue.
    
    Creates a new GitHub issue or updates an existing one if already synced.
    """
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured",
        )
    
    # Get the task
    task = await session.get(Task, request.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value() if settings.github.token else None,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        # Determine labels based on task type and status
        labels = [task.task_type.value]
        if task.priority:
            labels.append(f"priority:{task.priority.value}")
        if task.status == TaskStatus.BACKLOG:
            labels.append("ready-for-dev")
        elif task.status == TaskStatus.IN_PROGRESS:
            labels.append("in-progress")
        elif task.status == TaskStatus.IN_REVIEW:
            labels.append("in-review")
        
        # Build issue body
        body_parts = []
        if task.description:
            body_parts.append(task.description)
        if task.story_points:
            body_parts.append(f"\n**Story Points:** {task.story_points}")
        if task.acceptance_criteria:
            body_parts.append("\n## Acceptance Criteria")
            for ac in task.acceptance_criteria:
                if isinstance(ac, dict):
                    body_parts.append(f"- {ac}")
                else:
                    body_parts.append(f"- {ac}")
        if task.technical_notes:
            body_parts.append(f"\n## Technical Notes\n{task.technical_notes}")
        
        body_parts.append(f"\n---\n_Synced from SDLC Agent: Task ID `{task.id}`_")
        body = "\n".join(body_parts)
        
        # Check if already synced
        if task.external_id:
            # Update existing issue
            issue_number = int(task.external_id.split("#")[-1])
            issue = await github.update_issue(
                issue_number=issue_number,
                title=task.title,
                body=body,
                labels=labels,
            )
        else:
            # Create new issue
            issue = await github.create_issue(
                title=task.title,
                body=body,
                labels=labels,
            )
            # Store GitHub reference
            task.external_id = f"github#{issue.number}"
            await session.flush()
        
        await github.close()
        
        logger.info(
            "Task synced to GitHub",
            task_id=str(task.id),
            issue_number=issue.number,
        )
        
        return {
            "task_id": task.id,
            "github_issue_number": issue.number,
            "github_issue_url": issue.html_url,
            "synced": True,
        }
    
    except Exception as e:
        logger.exception("Failed to sync task to GitHub", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync: {str(e)}",
        )


@router.post("/sync-project/{project_id}", response_model=SyncAllResponse)
async def sync_project_to_github(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    task_types: list[str] = Query(default=["epic", "story", "task"]),
) -> dict[str, Any]:
    """
    Sync all tasks in a project to GitHub.
    
    Creates GitHub issues for all tasks that haven't been synced yet.
    """
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured",
        )
    
    # Get all unsynced tasks
    query = select(Task).where(
        Task.project_id == project_id,
        Task.external_id.is_(None),
    )
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    synced = []
    failed = []
    
    github = GitHubService(
        token=settings.github.token.get_secret_value() if settings.github.token else None,
        owner=settings.github.owner,
        repo=settings.github.repo,
    )
    
    for task in tasks:
        if task.task_type.value not in task_types:
            continue
            
        try:
            labels = [task.task_type.value]
            if task.priority:
                labels.append(f"priority:{task.priority.value}")
            
            body = task.description or ""
            if task.story_points:
                body += f"\n\n**Story Points:** {task.story_points}"
            body += f"\n\n---\n_Synced from SDLC Agent: Task ID `{task.id}`_"
            
            issue = await github.create_issue(
                title=task.title,
                body=body,
                labels=labels,
            )
            
            task.external_id = f"github#{issue.number}"
            synced.append({
                "task_id": str(task.id),
                "title": task.title,
                "issue_number": issue.number,
                "url": issue.html_url,
            })
            
        except Exception as e:
            failed.append({
                "task_id": str(task.id),
                "title": task.title,
                "error": str(e),
            })
    
    await session.flush()
    await github.close()
    
    return {
        "synced_count": len(synced),
        "failed_count": len(failed),
        "details": synced + [{"failed": True, **f} for f in failed],
    }


@router.get("/issues", response_model=list[GitHubIssueResponse])
async def list_github_issues(
    state: str = Query(default="open"),
    labels: str | None = Query(default=None),
    per_page: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    """List issues from the connected GitHub repository."""
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value() if settings.github.token else None,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        label_list = labels.split(",") if labels else None
        issues = await github.list_issues(
            state=state,
            labels=label_list,
            per_page=per_page,
        )
        await github.close()
        
        return [
            {
                "number": issue.number,
                "title": issue.title,
                "state": issue.state.value,
                "labels": issue.labels,
                "html_url": issue.html_url,
            }
            for issue in issues
        ]
    
    except Exception as e:
        logger.exception("Failed to list GitHub issues", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list issues: {str(e)}",
        )


@router.post("/import-issue", response_model=dict[str, Any])
async def import_github_issue(
    request: ImportIssueRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Import a GitHub issue as a task in SDLC Agent.
    
    Converts a GitHub issue to a local task for tracking.
    """
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value() if settings.github.token else None,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        issue = await github.get_issue(request.issue_number)
        await github.close()
        
        # Determine task type from labels
        task_type = TaskType.TASK
        for label in issue.labels:
            if label in ["epic", "story", "task", "bug", "spike"]:
                task_type = TaskType(label)
                break
        
        # Determine priority from labels
        priority = TaskPriority.MEDIUM
        for label in issue.labels:
            if label.startswith("priority:"):
                priority_str = label.split(":")[1]
                if priority_str in ["critical", "high", "medium", "low"]:
                    priority = TaskPriority(priority_str)
                break
        
        # Create task
        task = Task(
            project_id=request.project_id,
            title=issue.title,
            description=issue.body,
            task_type=task_type,
            status=TaskStatus.BACKLOG if issue.state.value == "open" else TaskStatus.DONE,
            priority=priority,
            external_id=f"github#{issue.number}",
            labels=[l for l in issue.labels if not l.startswith("priority:")],
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        
        logger.info(
            "Imported GitHub issue as task",
            issue_number=issue.number,
            task_id=str(task.id),
        )
        
        return {
            "success": True,
            "task_id": str(task.id),
            "title": task.title,
            "task_type": task.task_type.value,
            "imported_from": issue.html_url,
        }
    
    except Exception as e:
        logger.exception("Failed to import GitHub issue", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import: {str(e)}",
        )


@router.get("/repository")
async def get_repository_info() -> dict[str, Any]:
    """Get information about the connected GitHub repository."""
    settings = get_settings()
    if not settings.github.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub integration not configured",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value() if settings.github.token else None,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        repo = await github.get_repository()
        await github.close()
        
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "html_url": repo.html_url,
            "default_branch": repo.default_branch,
            "private": repo.private,
        }
    
    except Exception as e:
        logger.exception("Failed to get repository info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get repository: {str(e)}",
        )
