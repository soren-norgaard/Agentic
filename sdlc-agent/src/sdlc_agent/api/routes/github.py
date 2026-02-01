# =============================================================================
# SDLC Agent - GitHub Integration Routes
# =============================================================================

from __future__ import annotations

import re
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Task, Project, TaskType, TaskStatus, TaskPriority, Artifact, get_session
from sdlc_agent.services.github_service import (
    GitHubService,
    GitHubIssue,
    GitHubIssueState,
    GitHubLabel,
    get_github_service,
)


# =============================================================================
# Helper Functions
# =============================================================================


def parse_github_url(url: str | None) -> tuple[str, str] | None:
    """
    Parse a GitHub repository URL to extract owner and repo.
    
    Supports formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - http://github.com/owner/repo
    - git@github.com:owner/repo.git
    
    Returns:
        Tuple of (owner, repo) or None if URL is not a valid GitHub URL.
    """
    if not url:
        return None
    
    # HTTPS format: https://github.com/owner/repo(.git)?
    https_match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        url.strip()
    )
    if https_match:
        return https_match.group(1), https_match.group(2)
    
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        url.strip()
    )
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    
    return None


async def get_github_config_for_project(
    project_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[str, str]:
    """
    Get GitHub owner/repo for a project.
    
    First checks project's repository_url, falls back to global settings.
    
    Returns:
        Tuple of (owner, repo)
        
    Raises:
        HTTPException if no GitHub configuration is available.
    """
    settings = get_settings()
    
    # First, try to get from project's repository_url
    project = await session.get(Project, project_id)
    if project and project.repository_url:
        parsed = parse_github_url(project.repository_url)
        if parsed:
            logger.debug(
                "Using project repository_url for GitHub sync",
                project_id=str(project_id),
                owner=parsed[0],
                repo=parsed[1],
            )
            return parsed
    
    # Fall back to global settings
    if settings.github.owner and settings.github.repo:
        return settings.github.owner, settings.github.repo
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No GitHub repository configured. Set repository_url on the project or configure GITHUB_OWNER and GITHUB_REPO.",
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


class GitHubProjectResponse(BaseModel):
    """GitHub Project v2 response."""
    id: str
    number: int
    title: str
    url: str


class SyncToProjectRequest(BaseModel):
    """Request to sync tasks to a GitHub Project board."""
    project_number: int
    status_mapping: dict[str, str] = Field(
        default={
            "backlog": "Backlog",
            "todo": "To Do",
            "in_progress": "In Progress",
            "in_review": "In Review",
            "done": "Done",
            "cancelled": "Done",
        },
        description="Map SDLC task status to GitHub Project column names",
    )


class SyncToProjectResponse(BaseModel):
    """Response after syncing tasks to GitHub Project."""
    synced_count: int
    failed_count: int
    project_url: str
    details: list[dict[str, Any]]


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
    Uses the task's project repository_url if set, otherwise falls back to global config.
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Get the task
    task = await session.get(Task, request.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found",
        )
    
    # Get GitHub owner/repo for this task's project
    owner, repo = await get_github_config_for_project(task.project_id, session)
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=owner,
            repo=repo,
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
        
        # Fetch developer brief artifact for this task
        developer_brief = None
        brief_query = select(Artifact).where(
            Artifact.task_id == task.id,
            Artifact.artifact_type == "developer_brief",
        ).order_by(Artifact.version.desc()).limit(1)
        brief_result = await session.execute(brief_query)
        developer_brief = brief_result.scalar_one_or_none()
        
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
                    # Format Given/When/Then style
                    given = ac.get('Given', '')
                    when = ac.get('When', '')
                    then = ac.get('Then', '')
                    if given or when or then:
                        body_parts.append(f"- **Given** {given}")
                        body_parts.append(f"  **When** {when}")
                        body_parts.append(f"  **Then** {then}")
                    else:
                        body_parts.append(f"- {ac}")
                else:
                    body_parts.append(f"- {ac}")
        if task.technical_notes:
            body_parts.append(f"\n## Technical Notes\n{task.technical_notes}")
        
        # Include developer brief if available
        if developer_brief and developer_brief.content:
            body_parts.append("\n## Developer Brief")
            body_parts.append("\n<details>")
            body_parts.append("<summary>Click to expand implementation guidance</summary>")
            body_parts.append(f"\n{developer_brief.content}")
            body_parts.append("\n</details>")
        
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
    include_synced: bool = Query(default=False, description="If true, also update already synced tasks"),
) -> dict[str, Any]:
    """
    Sync all tasks in a project to GitHub.
    
    Creates GitHub issues for all tasks that haven't been synced yet.
    If include_synced=true, also updates existing synced issues with latest data.
    Uses the project's repository_url if set, otherwise falls back to global config.
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Get GitHub owner/repo for this project
    owner, repo = await get_github_config_for_project(project_id, session)
    
    # Get tasks based on include_synced flag
    if include_synced:
        # Get all tasks (both synced and unsynced)
        query = select(Task).where(Task.project_id == project_id)
    else:
        # Get only unsynced tasks
        query = select(Task).where(
            Task.project_id == project_id,
            Task.external_id.is_(None),
        )
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    synced = []
    failed = []
    
    github = GitHubService(
        token=settings.github.token.get_secret_value(),
        owner=owner,
        repo=repo,
    )
    
    for task in tasks:
        if task.task_type.value not in task_types:
            continue
            
        try:
            # Fetch developer brief artifact for this task
            brief_query = select(Artifact).where(
                Artifact.task_id == task.id,
                Artifact.artifact_type == "developer_brief",
            ).order_by(Artifact.version.desc()).limit(1)
            brief_result = await session.execute(brief_query)
            developer_brief = brief_result.scalar_one_or_none()
            
            # Build labels
            labels = [task.task_type.value]
            if task.priority:
                labels.append(f"priority:{task.priority.value}")
            if task.status == TaskStatus.BACKLOG:
                labels.append("ready-for-dev")
            elif task.status == TaskStatus.IN_PROGRESS:
                labels.append("in-progress")
            elif task.status == TaskStatus.IN_REVIEW:
                labels.append("in-review")
            
            # Build rich body with all details
            body_parts = []
            if task.description:
                body_parts.append(task.description)
            if task.story_points:
                body_parts.append(f"\n**Story Points:** {task.story_points}")
            if task.acceptance_criteria:
                body_parts.append("\n## Acceptance Criteria")
                for ac in task.acceptance_criteria:
                    if isinstance(ac, dict):
                        given = ac.get('Given', '')
                        when = ac.get('When', '')
                        then = ac.get('Then', '')
                        if given or when or then:
                            body_parts.append(f"- **Given** {given}")
                            body_parts.append(f"  **When** {when}")
                            body_parts.append(f"  **Then** {then}")
                        else:
                            body_parts.append(f"- {ac}")
                    else:
                        body_parts.append(f"- {ac}")
            if task.technical_notes:
                body_parts.append(f"\n## Technical Notes\n{task.technical_notes}")
            
            # Include developer brief if available
            if developer_brief and developer_brief.content:
                body_parts.append("\n## Developer Brief")
                body_parts.append("\n<details>")
                body_parts.append("<summary>Click to expand implementation guidance</summary>")
                body_parts.append(f"\n{developer_brief.content}")
                body_parts.append("\n</details>")
            
            body_parts.append(f"\n---\n_Synced from SDLC Agent: Task ID `{task.id}`_")
            body = "\n".join(body_parts)
            
            # Check if already synced - update or create
            if task.external_id:
                # Update existing issue
                issue_number = int(task.external_id.split("#")[-1])
                issue = await github.update_issue(
                    issue_number=issue_number,
                    title=task.title,
                    body=body,
                    labels=labels,
                )
                action = "updated"
            else:
                # Create new issue
                issue = await github.create_issue(
                    title=task.title,
                    body=body,
                    labels=labels,
                )
                task.external_id = f"github#{issue.number}"
                action = "created"
            
            synced.append({
                "task_id": str(task.id),
                "title": task.title,
                "issue_number": issue.number,
                "url": issue.html_url,
                "action": action,
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
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: uuid.UUID | None = Query(default=None),
    state: str = Query(default="open"),
    labels: str | None = Query(default=None),
    per_page: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    """
    List issues from a GitHub repository.
    
    If project_id is provided, uses the project's repository_url.
    Otherwise falls back to global GITHUB_OWNER/GITHUB_REPO settings.
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Determine owner/repo
    if project_id:
        owner, repo = await get_github_config_for_project(project_id, session)
    elif settings.github.owner and settings.github.repo:
        owner, repo = settings.github.owner, settings.github.repo
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub repository configured. Provide project_id or set GITHUB_OWNER and GITHUB_REPO.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=owner,
            repo=repo,
        )
        
        label_list = labels.split(",") if labels else None
        # Convert state string to enum
        issue_state = GitHubIssueState(state) if state else GitHubIssueState.OPEN
        issues = await github.list_issues(
            state=issue_state,
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
    Uses the project's repository_url if set, otherwise falls back to global config.
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Get GitHub owner/repo for this project
    owner, repo = await get_github_config_for_project(request.project_id, session)
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=owner,
            repo=repo,
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


# =============================================================================
# GitHub Projects v2 Routes
# =============================================================================


@router.get("/projects", response_model=list[GitHubProjectResponse])
async def list_github_projects() -> list[dict[str, Any]]:
    """List all GitHub Projects v2 for the configured owner."""
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        projects = await github.list_projects()
        await github.close()
        
        return [
            {
                "id": p.id,
                "number": p.number,
                "title": p.title,
                "url": p.url,
            }
            for p in projects
        ]
    
    except Exception as e:
        logger.exception("Failed to list GitHub projects", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


@router.post("/projects", response_model=GitHubProjectResponse)
async def create_github_project(
    title: str = Query(..., description="Title for the new project"),
) -> dict[str, Any]:
    """Create a new GitHub Project v2."""
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        project = await github.create_project(title)
        await github.close()
        
        return {
            "id": project.id,
            "number": project.number,
            "title": project.title,
            "url": project.url,
        }
    
    except Exception as e:
        logger.exception("Failed to create GitHub project", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.post("/sync-to-project/{project_id}", response_model=SyncToProjectResponse)
async def sync_project_to_github_project(
    project_id: uuid.UUID,
    request: SyncToProjectRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Sync all tasks in an SDLC project to a GitHub Project board.
    
    This adds all synced issues to the GitHub Project and sets their status
    column based on the task's current status in SDLC Agent.
    
    Prerequisites:
    - Tasks must first be synced to GitHub Issues (use /sync-project/{id} first)
    - The GitHub Project must exist with the specified project_number
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Get GitHub owner/repo for this project
    owner, repo = await get_github_config_for_project(project_id, session)
    
    # Get all tasks that have been synced to GitHub (have external_id)
    query = select(Task).where(
        Task.project_id == project_id,
        Task.external_id.isnot(None),
    )
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No synced tasks found. Sync tasks to GitHub Issues first using /sync-project/{id}.",
        )
    
    github = GitHubService(
        token=settings.github.token.get_secret_value(),
        owner=owner,
        repo=repo,
    )
    
    # Get or verify the project exists
    project = await github.get_project(request.project_number)
    if not project:
        await github.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GitHub Project {request.project_number} not found. Create it first or check the project number.",
        )
    
    synced = []
    failed = []
    
    for task in tasks:
        try:
            # Extract issue number from external_id (format: "github#123")
            if not task.external_id or not task.external_id.startswith("github#"):
                continue
            
            issue_number = int(task.external_id.split("#")[-1])
            
            # Map task status to project column
            status_name = request.status_mapping.get(
                task.status.value,
                "Todo"  # Default to Todo if no mapping
            )
            
            # Add issue to project with status
            item = await github.sync_issue_to_project(
                project_number=request.project_number,
                issue_number=issue_number,
                status=status_name,
            )
            
            synced.append({
                "task_id": str(task.id),
                "title": task.title,
                "issue_number": issue_number,
                "project_item_id": item.id,
                "status": status_name,
            })
            
        except Exception as e:
            failed.append({
                "task_id": str(task.id),
                "title": task.title,
                "error": str(e),
            })
    
    await github.close()
    
    return {
        "synced_count": len(synced),
        "failed_count": len(failed),
        "project_url": project.url,
        "details": synced + [{"failed": True, **f} for f in failed],
    }


@router.get("/projects/{project_number}/fields")
async def get_project_fields(
    project_number: int,
) -> dict[str, Any]:
    """Get fields and their options for a GitHub Project v2."""
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        project = await github.get_project(project_number)
        await github.close()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_number} not found",
            )
        
        return {
            "project_id": project.id,
            "project_number": project.number,
            "project_title": project.title,
            "fields": [
                {
                    "id": f.id,
                    "name": f.name,
                    "type": f.field_type,
                    "options": f.options,
                }
                for f in (project.fields or [])
            ],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get project fields", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project fields: {str(e)}",
        )


class UpdateFieldOptionsRequest(BaseModel):
    """Request to update field options for a GitHub Project v2."""
    field_name: str = Field(default="Status", description="Name of the field to update")
    options: list[dict[str, str]] | None = Field(
        default=None,
        description="List of options with 'name', 'color' (GRAY, BLUE, GREEN, YELLOW, ORANGE, RED, PINK, PURPLE), and 'description'. If null, uses SDLC Agent defaults.",
        examples=[[
            {"name": "Backlog", "color": "GRAY", "description": "Not yet started"},
            {"name": "To Do", "color": "BLUE", "description": "Ready to work on"},
            {"name": "In Progress", "color": "YELLOW", "description": "Currently being worked on"},
            {"name": "In Review", "color": "PURPLE", "description": "Awaiting review"},
            {"name": "Done", "color": "GREEN", "description": "Completed"},
        ]],
    )


@router.put("/projects/{project_number}/fields/options")
async def update_project_field_options(
    project_number: int,
    request: UpdateFieldOptionsRequest,
) -> dict[str, Any]:
    """
    Update the options for a single-select field in a GitHub Project v2.
    
    This allows programmatic configuration of project columns/statuses to match
    SDLC Agent's workflow (Backlog, To Do, In Progress, In Review, Done).
    
    If no options are provided, uses the SDLC Agent default columns.
    
    Available colors: GRAY, BLUE, GREEN, YELLOW, ORANGE, RED, PINK, PURPLE
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        updated_field = await github.update_project_field_options(
            project_number=project_number,
            field_name=request.field_name,
            options=request.options,
        )
        await github.close()
        
        logger.info(
            "Updated project field options",
            project_number=project_number,
            field_name=request.field_name,
            options_count=len(updated_field.options) if updated_field.options else 0,
        )
        
        return {
            "success": True,
            "project_number": project_number,
            "field": {
                "id": updated_field.id,
                "name": updated_field.name,
                "type": updated_field.field_type,
                "options": updated_field.options,
            },
            "message": f"Successfully updated {len(updated_field.options or [])} options for field '{request.field_name}'",
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update project field options", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project field options: {str(e)}",
        )


# =============================================================================
# Pull from GitHub (Bidirectional Sync)
# =============================================================================

# Map GitHub Project column names to SDLC Agent TaskStatus
GITHUB_TO_SDLC_STATUS: dict[str, TaskStatus] = {
    "backlog": TaskStatus.BACKLOG,
    "to do": TaskStatus.TODO,
    "todo": TaskStatus.TODO,
    "in progress": TaskStatus.IN_PROGRESS,
    "in_progress": TaskStatus.IN_PROGRESS,
    "in review": TaskStatus.IN_REVIEW,
    "in_review": TaskStatus.IN_REVIEW,
    "review": TaskStatus.IN_REVIEW,
    "done": TaskStatus.DONE,
    "closed": TaskStatus.DONE,
    "blocked": TaskStatus.BLOCKED,
}


class PullFromGitHubRequest(BaseModel):
    """Request to pull changes from GitHub."""
    project_number: int = Field(
        description="The GitHub Project number to sync from"
    )


class PullFromGitHubResponse(BaseModel):
    """Response after pulling changes from GitHub."""
    synced_count: int
    skipped_count: int
    not_found_count: int
    details: list[dict[str, Any]]


@router.post("/pull-from-github/{project_id}", response_model=PullFromGitHubResponse)
async def pull_from_github(
    project_id: uuid.UUID,
    request: PullFromGitHubRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Pull changes from GitHub to sync task statuses.
    
    This fetches all items from the specified GitHub Project and updates
    the corresponding SDLC Agent tasks to match their GitHub status.
    
    This is an alternative to webhooks for bidirectional sync - manually
    trigger when you want to pull changes from GitHub.
    """
    settings = get_settings()
    if not settings.github.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token not configured. Set GITHUB_TOKEN in environment.",
        )
    
    # Get GitHub config for project
    owner, repo = await get_github_config_for_project(project_id, session)
    
    try:
        github = GitHubService(
            token=settings.github.token.get_secret_value(),
            owner=owner,
            repo=repo,
        )
        
        # Fetch all project items with their current status
        items = await github.get_project_items_with_status(request.project_number)
        await github.close()
        
        synced_count = 0
        skipped_count = 0
        not_found_count = 0
        details = []
        
        for item in items:
            issue_number = item["issue_number"]
            issue_title = item["issue_title"]
            issue_state = item["issue_state"]
            project_status = item["project_status"]
            
            # Find the corresponding task
            external_id = f"github#{issue_number}"
            query = select(Task).where(Task.external_id == external_id)
            result = await session.execute(query)
            task = result.scalar_one_or_none()
            
            if not task:
                not_found_count += 1
                details.append({
                    "issue_number": issue_number,
                    "issue_title": issue_title,
                    "action": "not_found",
                    "message": "No matching task found",
                })
                continue
            
            # Determine new status
            new_status = None
            
            # If issue is closed, mark as done
            if issue_state == "closed":
                new_status = TaskStatus.DONE
            # Otherwise, use project board status
            elif project_status:
                status_key = project_status.lower()
                new_status = GITHUB_TO_SDLC_STATUS.get(status_key)
            
            if new_status and task.status != new_status:
                old_status = task.status
                task.status = new_status
                synced_count += 1
                details.append({
                    "issue_number": issue_number,
                    "issue_title": issue_title,
                    "task_id": str(task.id),
                    "action": "updated",
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "github_status": project_status,
                })
                logger.info(
                    "Updated task status from GitHub",
                    task_id=str(task.id),
                    issue_number=issue_number,
                    old_status=old_status.value,
                    new_status=new_status.value,
                )
            else:
                skipped_count += 1
                details.append({
                    "issue_number": issue_number,
                    "issue_title": issue_title,
                    "task_id": str(task.id),
                    "action": "skipped",
                    "reason": "Status unchanged" if new_status else "Unknown GitHub status",
                    "current_status": task.status.value,
                    "github_status": project_status,
                })
        
        # Commit all changes
        await session.commit()
        
        logger.info(
            "Completed pull from GitHub",
            project_number=request.project_number,
            synced_count=synced_count,
            skipped_count=skipped_count,
            not_found_count=not_found_count,
        )
        
        return {
            "synced_count": synced_count,
            "skipped_count": skipped_count,
            "not_found_count": not_found_count,
            "details": details,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to pull from GitHub", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull from GitHub: {str(e)}",
        )