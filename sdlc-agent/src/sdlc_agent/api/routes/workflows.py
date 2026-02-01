# =============================================================================
# SDLC Agent - Workflow Routes
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.exceptions import EntityNotFoundError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import AgentExecution, Artifact, HumanInput, Project, Workflow, WorkflowStatus, get_session

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    project_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=20000)
    initial_state: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    status: WorkflowStatus
    current_state: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('started_at', 'completed_at', 'created_at', 'updated_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class WorkflowListResponse(BaseModel):
    """Schema for paginated workflow list."""

    items: list[WorkflowResponse]
    total: int
    page: int
    page_size: int
    pages: int


class WorkflowActionRequest(BaseModel):
    """Schema for workflow actions (start, pause, resume, cancel, retry)."""

    action: str = Field(..., pattern="^(start|pause|resume|cancel|retry)$")


class HumanInputRequest(BaseModel):
    """Schema for submitting human input."""

    input_id: uuid.UUID
    response: dict[str, Any]


class AgentExecutionResponse(BaseModel):
    """Schema for agent execution response."""

    id: uuid.UUID
    workflow_id: uuid.UUID
    agent_type: str
    agent_name: str
    started_at: datetime
    completed_at: datetime | None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    success: bool | None
    error_message: str | None
    tokens_used: int
    iterations: int

    class Config:
        from_attributes = True

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class HumanInputResponse(BaseModel):
    """Schema for human input response."""

    id: uuid.UUID
    workflow_id: uuid.UUID
    request_type: str
    prompt: str
    context: dict[str, Any]
    response: dict[str, Any] | None
    is_resolved: bool
    requested_at: datetime
    responded_at: datetime | None

    class Config:
        from_attributes = True

    @field_serializer('requested_at', 'responded_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class HumanInputListResponse(BaseModel):
    """Schema for listing human inputs."""

    items: list[HumanInputResponse]
    total: int


class ArtifactResponse(BaseModel):
    """Schema for artifact response."""

    id: uuid.UUID
    workflow_id: uuid.UUID | None
    task_id: uuid.UUID | None
    name: str
    artifact_type: str
    file_path: str | None
    content: str | None
    extra_data: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ArtifactListResponse(BaseModel):
    """Schema for listing artifacts."""

    items: list[ArtifactResponse]
    total: int


class DevelopmentPrepRequest(BaseModel):
    """Schema for requesting development preparation."""

    story_id: str = Field(..., description="ID of the story to prepare")
    story_title: str = Field(..., description="Title of the story")
    story_description: str = Field(default="", description="Description of the story")
    acceptance_criteria: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    github_issue_number: int | None = Field(None, description="GitHub issue number to post brief to")


class DevelopmentPrepResponse(BaseModel):
    """Schema for development preparation response."""

    success: bool
    brief_artifact_id: uuid.UUID | None = None
    brief_content: str | None = None
    github_comment_posted: bool = False
    message: str


class WorkflowContinueRequest(BaseModel):
    """Schema for continuing a workflow to next phase."""

    target_phase: str = Field(..., description="Phase to continue to")
    config: dict[str, Any] = Field(default_factory=dict)


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


@router.get("/{workflow_id}/executions", response_model=list[AgentExecutionResponse])
async def get_workflow_executions(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AgentExecution]:
    """
    Get all agent executions for a workflow.

    Args:
        workflow_id: Workflow UUID
        session: Database session

    Returns:
        List of agent executions
    """
    # Verify workflow exists
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    # Get executions
    query = select(AgentExecution).where(
        AgentExecution.workflow_id == workflow_id
    ).order_by(AgentExecution.started_at.desc())
    
    result = await session.execute(query)
    return list(result.scalars().all())


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

    from sdlc_agent.services.workflow_executor import enqueue_workflow

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    action = data.action

    if action == "start":
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Cannot start workflow in {workflow.status} status")
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(UTC)
        
        # Enqueue workflow for background execution
        await enqueue_workflow(
            workflow_id=str(workflow_id),
            project_id=str(workflow.project_id),
            objective=workflow.description or workflow.name,
            config=workflow.current_state,
        )

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

    elif action == "retry":
        # Allow retrying failed workflows
        if workflow.status != WorkflowStatus.FAILED:
            raise ValueError(f"Cannot retry workflow in {workflow.status} status. Only failed workflows can be retried.")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.error_message = None
        workflow.retry_count += 1
        
        # Re-enqueue with current state
        await enqueue_workflow(
            workflow_id=str(workflow_id),
            project_id=str(workflow.project_id),
            objective=workflow.description or workflow.name,
            config=workflow.current_state or {},
        )

    await session.flush()
    await session.refresh(workflow)

    logger.info(
        "Workflow action performed",
        workflow_id=str(workflow_id),
        action=action,
        new_status=workflow.status.value,
    )
    return workflow


@router.post("/{workflow_id}/continue", response_model=WorkflowResponse)
async def continue_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowContinueRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Workflow:
    """
    Continue a workflow to the next phase.

    This allows manual progression through phases after completion.
    Useful when the workflow has completed a phase but needs to continue.
    """
    from datetime import UTC, datetime

    from sdlc_agent.services.workflow_executor import enqueue_workflow

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    # Allow continuation from completed or paused status
    if workflow.status not in {WorkflowStatus.COMPLETED, WorkflowStatus.PAUSED}:
        raise ValueError(f"Cannot continue workflow in {workflow.status} status")

    # Update status and state
    workflow.status = WorkflowStatus.RUNNING
    
    # Merge the current state with continuation config
    current_state = workflow.current_state or {}
    current_state["target_phase"] = data.target_phase
    current_state["continue_from_phase"] = True
    current_state.update(data.config)
    workflow.current_state = current_state

    await session.flush()
    await session.refresh(workflow)

    # Enqueue for continued execution
    await enqueue_workflow(
        workflow_id=str(workflow_id),
        project_id=str(workflow.project_id),
        objective=workflow.description or workflow.name,
        config={
            **current_state,
            "target_phase": data.target_phase,
        },
    )

    logger.info(
        "Workflow continuation requested",
        workflow_id=str(workflow_id),
        target_phase=data.target_phase,
    )
    return workflow


@router.post("/{workflow_id}/prepare-development", response_model=DevelopmentPrepResponse)
async def prepare_development(
    workflow_id: uuid.UUID,
    data: DevelopmentPrepRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Prepare development for a specific story.

    Creates a Developer Brief artifact and optionally posts it to GitHub.
    This is a manual trigger for the Development Preparation Agent's work.
    """
    from sdlc_agent.agents.developer import DeveloperBrief
    from sdlc_agent.services.artifact_service import ArtifactService

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    # Create a developer brief
    brief = DeveloperBrief(
        story_id=data.story_id,
        story_title=data.story_title,
        requirements_addressed=data.requirement_ids,
        acceptance_criteria=data.acceptance_criteria,
        architecture_context=f"Story: {data.story_description}",
        suggested_approach="Review the story details and implement according to acceptance criteria.",
        implementation_steps=[
            "Review requirements and acceptance criteria",
            "Identify files to create or modify",
            "Implement the feature",
            "Write unit tests",
            "Update documentation if needed",
            "Create pull request",
        ],
        pre_implementation_checklist=[
            "Create feature branch",
            "Set up local development environment",
            "Review related code patterns",
        ],
        definition_of_done=[
            "All acceptance criteria met",
            "Unit tests passing",
            "Code reviewed and approved",
            "No linting errors",
            "Documentation updated",
        ],
    )

    brief_markdown = brief.to_markdown()

    # Save as artifact
    artifact_service = ArtifactService(session)
    artifact = await artifact_service.create_artifact(
        workflow_id=workflow_id,
        name=f"Developer Brief - {data.story_title}",
        artifact_type="developer_brief",
        content=brief_markdown,
        extra_data={
            "story_id": data.story_id,
            "story_title": data.story_title,
            "requirement_ids": data.requirement_ids,
        },
    )

    # Post to GitHub if issue number provided
    github_posted = False
    if data.github_issue_number:
        try:
            from sdlc_agent.services.github_service import GitHubService

            github = GitHubService()
            await github.add_issue_comment(
                issue_number=data.github_issue_number,
                body=brief_markdown,
            )
            await github.add_labels(
                issue_number=data.github_issue_number,
                labels=["ready-for-dev"],
            )
            github_posted = True
        except Exception as e:
            logger.warning(
                "Failed to post brief to GitHub",
                error=str(e),
                issue_number=data.github_issue_number,
            )

    return {
        "success": True,
        "brief_artifact_id": artifact.id,
        "brief_content": brief_markdown,
        "github_comment_posted": github_posted,
        "message": f"Developer Brief created for {data.story_title}",
    }


@router.get("/{workflow_id}/developer-briefs")
async def get_developer_briefs(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactListResponse:
    """
    Get all developer briefs for a workflow.
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    query = select(Artifact).where(
        Artifact.workflow_id == workflow_id,
        Artifact.artifact_type == "developer_brief",
    ).order_by(Artifact.created_at.desc())

    result = await session.execute(query)
    artifacts = list(result.scalars().all())

    return {"items": artifacts, "total": len(artifacts)}


# =============================================================================
# Code Review Endpoints
# =============================================================================


class ReviewPrepRequest(BaseModel):
    """Schema for requesting a code review brief."""

    pr_number: int
    pr_title: str
    story_id: str | None = None
    story_title: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    files_changed: list[dict[str, Any]] = Field(default_factory=list)


class ReviewPrepResponse(BaseModel):
    """Response for code review preparation."""

    success: bool
    brief_artifact_id: uuid.UUID
    brief_content: str
    github_comment_posted: bool
    message: str


@router.post("/{workflow_id}/prepare-review", response_model=ReviewPrepResponse)
async def prepare_code_review(
    workflow_id: uuid.UUID,
    data: ReviewPrepRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Prepare a code review brief for a PR.

    Creates a Review Brief artifact and posts it to the GitHub PR.
    This is a manual trigger for the Code Review Assistance Agent's work.
    """
    from sdlc_agent.agents.code_review import ReviewBrief
    from sdlc_agent.services.artifact_service import ArtifactService

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    # Create key files list from files_changed
    key_files = [
        {"path": f.get("filename", f.get("path", "")), "focus": "Changed file"}
        for f in data.files_changed[:10]  # Limit to 10 files
    ]

    # Create a review brief
    brief = ReviewBrief(
        pr_number=data.pr_number,
        pr_title=data.pr_title,
        story_id=data.story_id,
        acceptance_criteria=data.acceptance_criteria,
        key_files=key_files,
    )

    brief_markdown = brief.to_markdown()

    # Save as artifact
    artifact_service = ArtifactService(session)
    artifact = await artifact_service.create_artifact(
        workflow_id=workflow_id,
        name=f"Review Brief - PR #{data.pr_number}",
        artifact_type="review_brief",
        content=brief_markdown,
        extra_data={
            "pr_number": data.pr_number,
            "pr_title": data.pr_title,
            "story_id": data.story_id,
        },
    )

    # Post to GitHub PR
    github_posted = False
    try:
        from sdlc_agent.services.github_service import GitHubService

        github = GitHubService()
        await github.add_pr_comment(
            pr_number=data.pr_number,
            body=brief_markdown,
        )
        # Also add a label (PRs use issue number for labels)
        await github.add_labels(
            issue_number=data.pr_number,
            labels=["review-brief-posted"],
        )
        github_posted = True
    except Exception as e:
        logger.warning(
            "Failed to post review brief to GitHub",
            error=str(e),
            pr_number=data.pr_number,
        )

    return {
        "success": True,
        "brief_artifact_id": artifact.id,
        "brief_content": brief_markdown,
        "github_comment_posted": github_posted,
        "message": f"Review Brief created for PR #{data.pr_number}",
    }


@router.get("/{workflow_id}/review-briefs")
async def get_review_briefs(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactListResponse:
    """
    Get all review briefs for a workflow.
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    query = select(Artifact).where(
        Artifact.workflow_id == workflow_id,
        Artifact.artifact_type == "review_brief",
    ).order_by(Artifact.created_at.desc())

    result = await session.execute(query)
    artifacts = list(result.scalars().all())

    return {"items": artifacts, "total": len(artifacts)}


# =============================================================================
# Automated Code Review Endpoints
# =============================================================================


class AutoReviewRequest(BaseModel):
    """Schema for requesting automated code review."""

    pr_number: int = Field(..., description="GitHub PR number to review")
    auto_submit: bool = Field(
        default=False,
        description="Whether to auto-submit the review to GitHub"
    )
    review_mode: str = Field(
        default="COMMENT",
        description="Review mode: APPROVE, REQUEST_CHANGES, or COMMENT"
    )
    focus_areas: list[str] = Field(
        default_factory=lambda: ["security", "performance", "maintainability", "testing"],
        description="Areas to focus the review on"
    )


class AutoReviewResponse(BaseModel):
    """Response for automated code review."""

    success: bool
    pr_number: int
    files_analyzed: int
    findings_count: int
    review_brief: str | None = None
    review_submitted: bool = False
    artifact_id: uuid.UUID | None = None
    message: str


@router.post("/{workflow_id}/auto-review", response_model=AutoReviewResponse)
async def automated_code_review(
    workflow_id: uuid.UUID,
    data: AutoReviewRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Perform automated code review on a GitHub pull request.

    This endpoint:
    1. Fetches the PR files and diff from GitHub
    2. Analyzes the changes for code quality issues
    3. Generates a comprehensive review brief
    4. Optionally submits the review to GitHub

    The review focuses on:
    - Security vulnerabilities
    - Performance issues
    - Code maintainability
    - Testing coverage
    - Best practices adherence
    """
    from sdlc_agent.agents.code_review import ReviewBrief
    from sdlc_agent.services.artifact_service import ArtifactService
    from sdlc_agent.services.github_service import GitHubService

    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    github = GitHubService()

    # Fetch PR details
    try:
        pr = await github.get_pull_request(data.pr_number)
        pr_files = await github.get_pr_files(data.pr_number)
    except Exception as e:
        return {
            "success": False,
            "pr_number": data.pr_number,
            "files_analyzed": 0,
            "findings_count": 0,
            "review_submitted": False,
            "message": f"Failed to fetch PR #{data.pr_number}: {e}",
        }

    # Analyze files for issues
    findings = []
    security_patterns = [
        ("password", "Potential hardcoded password", "critical"),
        ("secret", "Potential hardcoded secret", "critical"),
        ("api_key", "Potential hardcoded API key", "critical"),
        ("apikey", "Potential hardcoded API key", "critical"),
        ("eval(", "Use of eval() - potential code injection risk", "major"),
        ("exec(", "Use of exec() - potential code injection risk", "major"),
        ("subprocess.call", "Shell command execution - verify input sanitization", "minor"),
        ("pickle.load", "Pickle deserialization - potential security risk", "major"),
        ("FIXME", "FIXME comment found - needs attention", "minor"),
        ("XXX", "XXX comment found - needs attention", "minor"),
    ]

    performance_patterns = [
        ("SELECT *", "SELECT * in SQL - consider selecting specific columns", "minor"),
        ("time.sleep", "Synchronous sleep - consider async alternatives", "info"),
    ]

    key_files = []
    for f in pr_files:
        filename = f.get("filename", "")
        patch = f.get("patch", "") or ""
        
        key_files.append({
            "path": filename,
            "focus": f"Changed: +{f.get('additions', 0)}/-{f.get('deletions', 0)}",
        })

        # Security analysis
        if "security" in data.focus_areas:
            for pattern, message, severity in security_patterns:
                if pattern.lower() in patch.lower():
                    findings.append({
                        "severity": severity,
                        "category": "security",
                        "file": filename,
                        "message": message,
                    })

        # Performance analysis
        if "performance" in data.focus_areas:
            for pattern, message, severity in performance_patterns:
                if pattern.lower() in patch.lower():
                    findings.append({
                        "severity": severity,
                        "category": "performance",
                        "file": filename,
                        "message": message,
                    })

    # Create review brief
    brief = ReviewBrief(
        pr_number=data.pr_number,
        pr_title=pr.title,
        story_id=None,  # Could be extracted from PR body/branch name
        key_files=key_files[:10],
        automated_findings=findings,
        functional_checklist=[
            {"item": "Code implements described functionality", "why": "Core requirement"},
            {"item": "Edge cases are handled appropriately", "why": "Robustness"},
            {"item": "Error handling is comprehensive", "why": "Reliability"},
        ],
        code_quality_checklist=[
            {"item": "Code is readable and well-named", "why": "Maintainability"},
            {"item": "No code duplication (DRY principle)", "why": "Maintainability"},
            {"item": "Functions are small and focused (SRP)", "why": "Clean code"},
        ],
        security_checklist=[
            {"item": "No secrets or credentials in code", "why": "Security"},
            {"item": "User input is validated and sanitized", "why": "Injection prevention"},
            {"item": "Sensitive data is not logged", "why": "Privacy"},
        ],
        testing_checklist=[
            {"item": "Unit tests cover new functionality", "why": "Coverage"},
            {"item": "Tests cover edge cases and error paths", "why": "Robustness"},
        ],
    )

    brief_markdown = brief.to_markdown()

    # Save as artifact
    artifact_service = ArtifactService(session)
    artifact = await artifact_service.create_artifact(
        workflow_id=workflow_id,
        name=f"Auto Review - PR #{data.pr_number}",
        artifact_type="review_brief",
        content=brief_markdown,
        extra_data={
            "pr_number": data.pr_number,
            "pr_title": pr.title,
            "files_analyzed": len(pr_files),
            "findings_count": len(findings),
            "focus_areas": data.focus_areas,
            "auto_submitted": data.auto_submit,
        },
    )

    # Submit review to GitHub if requested
    review_submitted = False
    if data.auto_submit:
        try:
            await github.submit_pr_review(
                pr_number=data.pr_number,
                body=brief_markdown,
                event=data.review_mode,
            )
            review_submitted = True
            logger.info(
                "Auto-submitted PR review",
                pr_number=data.pr_number,
                mode=data.review_mode,
            )
        except Exception as e:
            logger.warning(
                "Failed to submit review to GitHub",
                error=str(e),
                pr_number=data.pr_number,
            )

    return {
        "success": True,
        "pr_number": data.pr_number,
        "files_analyzed": len(pr_files),
        "findings_count": len(findings),
        "review_brief": brief_markdown,
        "review_submitted": review_submitted,
        "artifact_id": artifact.id,
        "message": f"Analyzed PR #{data.pr_number}: {len(pr_files)} files, {len(findings)} findings",
    }


@router.get("/{workflow_id}/inputs", response_model=HumanInputListResponse)
async def get_pending_human_inputs(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_resolved: bool = Query(False),
) -> dict[str, Any]:
    """
    Get pending human inputs for a workflow.

    Args:
        workflow_id: Workflow UUID
        session: Database session
        include_resolved: Whether to include resolved inputs

    Returns:
        List of human input requests
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    query = select(HumanInput).where(HumanInput.workflow_id == workflow_id)
    if not include_resolved:
        query = query.where(HumanInput.is_resolved == False)
    query = query.order_by(HumanInput.requested_at.desc())

    result = await session.execute(query)
    inputs = list(result.scalars().all())

    return {
        "items": inputs,
        "total": len(inputs),
    }


@router.get("/{workflow_id}/artifacts", response_model=ArtifactListResponse)
async def get_workflow_artifacts(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    artifact_type: str | None = Query(None),
) -> dict[str, Any]:
    """
    Get artifacts for a workflow.

    Args:
        workflow_id: Workflow UUID
        session: Database session
        artifact_type: Optional filter by type (requirements, code, test, doc, etc.)

    Returns:
        List of artifacts
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    query = select(Artifact).where(Artifact.workflow_id == workflow_id)
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)
    query = query.order_by(Artifact.created_at.desc())

    result = await session.execute(query)
    artifacts = list(result.scalars().all())

    return {
        "items": artifacts,
        "total": len(artifacts),
    }


@router.get("/{workflow_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    workflow_id: uuid.UUID,
    artifact_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Artifact:
    """
    Get a specific artifact by ID.

    Args:
        workflow_id: Workflow UUID
        artifact_id: Artifact UUID
        session: Database session

    Returns:
        Artifact details with content
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    artifact = await session.get(Artifact, artifact_id)
    if not artifact or artifact.workflow_id != workflow_id:
        raise EntityNotFoundError("Artifact", str(artifact_id))

    return artifact


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

    # Re-enqueue workflow for continued execution
    from sdlc_agent.services.workflow_executor import enqueue_workflow
    await enqueue_workflow(
        workflow_id=str(workflow_id),
        project_id=str(workflow.project_id),
        objective=workflow.description or workflow.name,
        config={
            **(workflow.current_state or {}),
            "human_input_response": data.response,
            "resume_from_input": True,
        },
    )

    logger.info(
        "Human input submitted",
        workflow_id=str(workflow_id),
        input_id=str(data.input_id),
    )
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """
    Delete a workflow.

    Args:
        workflow_id: Workflow UUID
        session: Database session
    """
    workflow = await session.get(Workflow, workflow_id)
    if not workflow:
        raise EntityNotFoundError("Workflow", str(workflow_id))

    # Don't allow deleting running workflows
    if workflow.status == WorkflowStatus.RUNNING:
        raise ValueError("Cannot delete a running workflow. Cancel it first.")

    await session.delete(workflow)
    await session.flush()

    logger.info("Workflow deleted", workflow_id=str(workflow_id))
