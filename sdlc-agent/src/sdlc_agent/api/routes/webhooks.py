# =============================================================================
# SDLC Agent - GitHub Webhook Handlers
# =============================================================================
"""
GitHub webhook endpoints for real-time bidirectional sync.

Handles the following GitHub events:
- issues: Issue created, edited, closed, reopened, labeled, unlabeled
- issue_comment: Comments on issues
- projects_v2_item: Project board card movements

To set up webhooks in GitHub:
1. Go to your repository Settings > Webhooks > Add webhook
2. Set Payload URL to: https://your-domain/api/v1/webhooks/github
3. Set Content type to: application/json
4. Set Secret to match GITHUB_WEBHOOK_SECRET
5. Select events: Issues, Issue comments, Projects v2 items
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import (
    PRLifecycleActorType,
    PRLifecycleEvent,
    PRLifecycleStage,
    Task,
    TaskStatus,
    get_session,
)


router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Status Mapping (GitHub Project Column -> SDLC Status)
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

# Map GitHub issue labels to status (for label-based workflow)
LABEL_TO_STATUS: dict[str, TaskStatus] = {
    "in-progress": TaskStatus.IN_PROGRESS,
    "in-review": TaskStatus.IN_REVIEW,
    "ready-for-dev": TaskStatus.TODO,
    "blocked": TaskStatus.BACKLOG,
}


# =============================================================================
# Schemas
# =============================================================================

class WebhookResponse(BaseModel):
    """Response after processing webhook."""
    received: bool
    event: str
    action: str | None = None
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

def verify_github_signature(
    payload: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """
    Verify that the webhook payload was signed by GitHub.
    
    GitHub sends a HMAC-SHA256 signature in the X-Hub-Signature-256 header.
    """
    if not signature_header:
        return False
    
    # GitHub sends signature as 'sha256=<hex_signature>'
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
    
    # Compute HMAC-SHA256
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    computed_signature = mac.hexdigest()
    
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)


async def find_task_by_github_issue(
    session: AsyncSession,
    issue_number: int,
    repo_full_name: str | None = None,
) -> Task | None:
    """
    Find a task that corresponds to a GitHub issue.
    
    Looks for tasks where external_id = 'github#<issue_number>'
    """
    external_id = f"github#{issue_number}"
    
    query = select(Task).where(Task.external_id == external_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


def parse_status_from_labels(labels: list[dict[str, Any]]) -> TaskStatus | None:
    """
    Determine task status from GitHub issue labels.
    """
    label_names = [label.get("name", "").lower() for label in labels]
    
    for label_name in label_names:
        if label_name in LABEL_TO_STATUS:
            return LABEL_TO_STATUS[label_name]
    
    return None


async def record_pr_lifecycle_event(
    session: AsyncSession,
    pr_number: int,
    stage: PRLifecycleStage,
    actor_type: PRLifecycleActorType,
    actor_name: str,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    links: list[dict[str, str]] | None = None,
    actor_avatar_url: str | None = None,
) -> PRLifecycleEvent:
    """
    Record a lifecycle event for a PR from webhook.
    """
    settings = get_settings()
    repository = f"{settings.github.owner}/{settings.github.repo}"
    
    event = PRLifecycleEvent(
        pr_number=pr_number,
        repository=repository,
        stage=stage,
        actor_type=actor_type,
        actor_name=actor_name,
        actor_avatar_url=actor_avatar_url,
        message=message,
        details=details or {},
        links=links or [],
    )
    
    session.add(event)
    await session.commit()
    await session.refresh(event)
    
    logger.info(
        "Recorded lifecycle event from webhook",
        pr_number=pr_number,
        stage=stage.value,
        actor=actor_name,
    )
    
    return event


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/github", response_model=WebhookResponse)
async def handle_github_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_github_event: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
    x_github_delivery: str | None = Header(None),
) -> WebhookResponse:
    """
    Handle incoming GitHub webhooks.
    
    Supported events:
    - issues: Sync issue state changes back to SDLC Agent
    - projects_v2_item: Sync project board movements
    """
    settings = get_settings()
    
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature if secret is configured
    if settings.github.webhook_secret:
        secret = settings.github.webhook_secret.get_secret_value()
        if not verify_github_signature(body, x_hub_signature_256, secret):
            logger.warning(
                "Invalid webhook signature",
                delivery_id=x_github_delivery,
                github_event=x_github_event,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    
    action = payload.get("action")
    
    logger.info(
        "Received GitHub webhook",
        github_event=x_github_event,
        action=action,
        delivery_id=x_github_delivery,
    )
    
    # Route to appropriate handler
    if x_github_event == "issues":
        return await handle_issues_event(session, payload, action)
    elif x_github_event == "pull_request":
        return await handle_pull_request_event(session, payload, action)
    elif x_github_event == "check_suite":
        return await handle_check_suite_event(session, payload, action)
    elif x_github_event == "projects_v2_item":
        return await handle_project_item_event(session, payload, action)
    elif x_github_event == "issue_comment":
        return await handle_issue_comment_event(session, payload, action)
    elif x_github_event == "ping":
        return WebhookResponse(
            received=True,
            event="ping",
            message="Webhook configured successfully!",
        )
    else:
        logger.debug("Ignoring unhandled event", github_event=x_github_event)
        return WebhookResponse(
            received=True,
            event=x_github_event or "unknown",
            action=action,
            message=f"Event '{x_github_event}' not handled",
        )


async def handle_issues_event(
    session: AsyncSession,
    payload: dict[str, Any],
    action: str | None,
) -> WebhookResponse:
    """
    Handle GitHub issues events.
    
    Actions:
    - opened: New issue (could create task)
    - edited: Issue updated (sync changes)
    - closed: Issue closed (mark done)
    - reopened: Issue reopened (change status)
    - labeled/unlabeled: Label changes (update status)
    """
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    
    if not issue_number:
        return WebhookResponse(
            received=True,
            event="issues",
            action=action,
            message="No issue number in payload",
        )
    
    # Find corresponding task
    task = await find_task_by_github_issue(session, issue_number)
    
    if not task:
        logger.debug(
            "No matching task for GitHub issue",
            issue_number=issue_number,
            action=action,
        )
        return WebhookResponse(
            received=True,
            event="issues",
            action=action,
            message=f"No task found for issue #{issue_number}",
        )
    
    updated = False
    old_status = task.status
    
    if action == "closed":
        # Issue closed -> mark as Done
        task.status = TaskStatus.DONE
        updated = True
        logger.info(
            "Task status updated from GitHub",
            task_id=str(task.id),
            issue_number=issue_number,
            old_status=old_status.value,
            new_status=TaskStatus.DONE.value,
        )
    
    elif action == "reopened":
        # Issue reopened -> mark as In Progress
        task.status = TaskStatus.IN_PROGRESS
        updated = True
        logger.info(
            "Task status updated from GitHub (reopened)",
            task_id=str(task.id),
            issue_number=issue_number,
            old_status=old_status.value,
            new_status=TaskStatus.IN_PROGRESS.value,
        )
    
    elif action in ("labeled", "unlabeled"):
        # Check if labels indicate status change
        labels = issue.get("labels", [])
        new_status = parse_status_from_labels(labels)
        
        if new_status and new_status != task.status:
            task.status = new_status
            updated = True
            logger.info(
                "Task status updated from GitHub labels",
                task_id=str(task.id),
                issue_number=issue_number,
                old_status=old_status.value,
                new_status=new_status.value,
            )
    
    elif action == "edited":
        # Sync title and description changes
        new_title = issue.get("title")
        new_body = issue.get("body", "")
        
        if new_title and new_title != task.title:
            task.title = new_title
            updated = True
        
        # Note: We don't sync body back to avoid overwriting structured data
        
        if updated:
            logger.info(
                "Task updated from GitHub",
                task_id=str(task.id),
                issue_number=issue_number,
            )
    
    if updated:
        await session.commit()
    
    return WebhookResponse(
        received=True,
        event="issues",
        action=action,
        message=f"Task {task.id} {'updated' if updated else 'unchanged'}",
    )


async def handle_project_item_event(
    session: AsyncSession,
    payload: dict[str, Any],
    action: str | None,
) -> WebhookResponse:
    """
    Handle GitHub Projects v2 item events.
    
    This is triggered when a card is moved between columns.
    The payload includes field changes which we use to detect status updates.
    """
    # projects_v2_item events have a different structure
    # We need to check for field_value changes
    
    changes = payload.get("changes", {})
    field_value = changes.get("field_value", {})
    
    # Get the new status column name
    to_value = field_value.get("to", {})
    column_name = to_value.get("name", "").lower() if isinstance(to_value, dict) else None
    
    if not column_name:
        # No field value change we care about
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message="No status column change detected",
        )
    
    # Get the issue number from the content
    # Note: projects_v2_item doesn't directly give us the issue number
    # We need to extract it from the content URL or content node_id
    projects_v2_item = payload.get("projects_v2_item", {})
    content_type = projects_v2_item.get("content_type")
    content_node_id = projects_v2_item.get("content_node_id")
    
    if content_type != "Issue":
        logger.debug(
            "Project item is not an Issue",
            content_type=content_type,
        )
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message=f"Content type '{content_type}' not handled",
        )
    
    # Extract issue number - this may require an API call in complex cases
    # For now, we'll try to find it in the payload or check all tasks
    
    # Some webhook payloads include the issue directly
    issue = payload.get("content", {}).get("issue", {})
    issue_number = issue.get("number") if issue else None
    
    if not issue_number:
        logger.warning(
            "Could not extract issue number from project item event",
            node_id=content_node_id,
        )
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message="Could not determine issue number",
        )
    
    # Find and update the task
    task = await find_task_by_github_issue(session, issue_number)
    
    if not task:
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message=f"No task found for issue #{issue_number}",
        )
    
    # Map column name to status
    new_status = GITHUB_TO_SDLC_STATUS.get(column_name)
    
    if not new_status:
        logger.debug(
            "Unknown project column",
            column_name=column_name,
        )
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message=f"Unknown column '{column_name}'",
        )
    
    if new_status != task.status:
        old_status = task.status
        task.status = new_status
        await session.commit()
        
        logger.info(
            "Task status updated from GitHub Project board",
            task_id=str(task.id),
            issue_number=issue_number,
            old_status=old_status.value,
            new_status=new_status.value,
            column_name=column_name,
        )
        
        return WebhookResponse(
            received=True,
            event="projects_v2_item",
            action=action,
            message=f"Task status changed: {old_status.value} -> {new_status.value}",
        )
    
    return WebhookResponse(
        received=True,
        event="projects_v2_item",
        action=action,
        message="No status change needed",
    )


async def handle_issue_comment_event(
    session: AsyncSession,
    payload: dict[str, Any],
    action: str | None,
) -> WebhookResponse:
    """
    Handle GitHub issue comment events.
    
    Could be used to:
    - Add comments to task activity log
    - Parse special commands from comments
    """
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    comment = payload.get("comment", {})
    comment_body = comment.get("body", "")
    
    # For now, just log the comment
    logger.debug(
        "Received issue comment",
        issue_number=issue_number,
        action=action,
        comment_length=len(comment_body),
    )
    
    # Future: Parse commands like "/status in-progress" from comments
    
    return WebhookResponse(
        received=True,
        event="issue_comment",
        action=action,
        message=f"Comment on issue #{issue_number} received",
    )


# =============================================================================
# Webhook Management Endpoints
# =============================================================================

@router.get("/status")
async def get_webhook_status() -> dict[str, Any]:
    """
    Check webhook configuration status.
    """
    settings = get_settings()
    
    return {
        "webhook_secret_configured": bool(settings.github.webhook_secret),
        "github_configured": settings.github.is_configured,
        "events_handled": [
            "issues",
            "pull_request",
            "check_suite",
            "projects_v2_item",
            "issue_comment",
            "ping",
        ],
        "status_mapping": {
            column: status.value 
            for column, status in GITHUB_TO_SDLC_STATUS.items()
        },
    }


# =============================================================================
# Pull Request Webhook Handlers
# =============================================================================

async def handle_pull_request_event(
    session: AsyncSession,
    payload: dict[str, Any],
    action: str | None,
) -> WebhookResponse:
    """
    Handle GitHub pull_request events.
    
    Actions:
    - opened: New PR -> auto-trigger code review + quality check
    - synchronize: PR updated (new commits) -> re-run quality check
    - closed: PR closed/merged -> update task status
    - review_requested: Notify about review request
    """
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    
    if not pr_number:
        return WebhookResponse(
            received=True,
            event="pull_request",
            action=action,
            message="No PR number in payload",
        )
    
    logger.info(
        "Pull request event received",
        pr_number=pr_number,
        action=action,
        title=pr.get("title"),
    )
    
    # Get author info
    author = pr.get("user", {})
    author_name = author.get("login", "unknown")
    author_avatar = author.get("avatar_url")
    
    if action == "opened":
        # Record PR created event
        await record_pr_lifecycle_event(
            session=session,
            pr_number=pr_number,
            stage=PRLifecycleStage.CREATED,
            actor_type=PRLifecycleActorType.USER,
            actor_name=author_name,
            actor_avatar_url=author_avatar,
            message=f"Pull request created from {pr.get('head', {}).get('ref', 'unknown')}",
        )
        
        # Record CI running event
        await record_pr_lifecycle_event(
            session=session,
            pr_number=pr_number,
            stage=PRLifecycleStage.CI_RUNNING,
            actor_type=PRLifecycleActorType.CI,
            actor_name="GitHub Actions",
        )
        
        # New PR opened - trigger code review AND security scan in parallel
        await asyncio.gather(
            trigger_auto_review(session, pr_number, pr),
            trigger_security_scan(session, pr_number, pr),
        )
        return WebhookResponse(
            received=True,
            event="pull_request",
            action=action,
            message=f"PR #{pr_number} opened - triggered auto-review and security scan",
        )
    
    elif action == "synchronize":
        # PR updated with new commits - re-run quality checks AND security scan in parallel
        await asyncio.gather(
            trigger_quality_check(session, pr_number, pr),
            trigger_security_scan(session, pr_number, pr),
        )
        return WebhookResponse(
            received=True,
            event="pull_request",
            action=action,
            message=f"PR #{pr_number} updated - triggered quality check and security scan",
        )
    
    elif action == "closed":
        # PR closed or merged
        merged = pr.get("merged", False)
        
        # Record lifecycle event
        await record_pr_lifecycle_event(
            session=session,
            pr_number=pr_number,
            stage=PRLifecycleStage.MERGED if merged else PRLifecycleStage.CLOSED,
            actor_type=PRLifecycleActorType.USER,
            actor_name=author_name,
            actor_avatar_url=author_avatar,
            message=f"Pull request {'merged to ' + pr.get('base', {}).get('ref', 'main') if merged else 'closed'}",
        )
        
        if merged:
            logger.info("PR merged", pr_number=pr_number)
            # Could update linked task to DONE here
        return WebhookResponse(
            received=True,
            event="pull_request",
            action=action,
            message=f"PR #{pr_number} {'merged' if merged else 'closed'}",
        )
    
    return WebhookResponse(
        received=True,
        event="pull_request",
        action=action,
        message=f"PR #{pr_number} action '{action}' noted",
    )


async def handle_check_suite_event(
    session: AsyncSession,
    payload: dict[str, Any],
    action: str | None,
) -> WebhookResponse:
    """
    Handle GitHub check_suite events.
    
    Used to track CI/CD status for PRs.
    """
    check_suite = payload.get("check_suite", {})
    conclusion = check_suite.get("conclusion")
    head_sha = check_suite.get("head_sha")
    
    # Get associated PRs
    prs = check_suite.get("pull_requests", [])
    
    if action == "completed" and prs:
        for pr in prs:
            pr_number = pr.get("number")
            logger.info(
                "CI check completed for PR",
                pr_number=pr_number,
                conclusion=conclusion,
                head_sha=head_sha[:8] if head_sha else None,
            )
            
            # Record CI completion event
            ci_stage = (
                PRLifecycleStage.CI_PASSED if conclusion == "success"
                else PRLifecycleStage.CI_FAILED if conclusion in ["failure", "timed_out"]
                else PRLifecycleStage.CI_RUNNING
            )
            
            await record_pr_lifecycle_event(
                session=session,
                pr_number=pr_number,
                stage=ci_stage,
                actor_type=PRLifecycleActorType.CI,
                actor_name="GitHub Actions",
                message=f"CI {conclusion}" if conclusion else "CI running",
                details={
                    "head_sha": head_sha[:8] if head_sha else None,
                },
            )
            
            # If CI passed, record review pending
            if conclusion == "success":
                await record_pr_lifecycle_event(
                    session=session,
                    pr_number=pr_number,
                    stage=PRLifecycleStage.CODE_REVIEW_PENDING,
                    actor_type=PRLifecycleActorType.BOT,
                    actor_name="SDLC Agent",
                )
    
    return WebhookResponse(
        received=True,
        event="check_suite",
        action=action,
        message=f"Check suite {conclusion or action} for {len(prs)} PRs",
    )


async def trigger_auto_review(
    session: AsyncSession,
    pr_number: int,
    pr_data: dict[str, Any],
) -> None:
    """
    Trigger automatic code review for a PR.
    
    This runs in the background and posts results to the PR.
    """
    try:
        from sdlc_agent.api.routes.prs import trigger_code_review, ReviewRequest
        
        # Create a mock request with default settings
        request = ReviewRequest(
            focus_areas=["security", "performance", "maintainability", "testing"],
            auto_submit=True,
        )
        
        # Run the review
        result = await trigger_code_review(
            pr_number=pr_number,
            request=request,
            session=session,
        )
        
        logger.info(
            "Auto-review completed",
            pr_number=pr_number,
            files_analyzed=result.files_analyzed,
            findings_count=result.findings_count,
            success=result.success,
        )
    except Exception as e:
        logger.error(
            "Failed to trigger auto-review",
            pr_number=pr_number,
            error=str(e),
        )


async def trigger_quality_check(
    session: AsyncSession,
    pr_number: int,
    pr_data: dict[str, Any],
) -> None:
    """
    Trigger quality check for a PR.
    """
    try:
        from sdlc_agent.api.routes.prs import run_quality_check, QualityCheckRequest
        
        request = QualityCheckRequest()
        
        result = await run_quality_check(
            pr_number=pr_number,
            request=request,
            session=session,
        )
        
        logger.info(
            "Quality check completed",
            pr_number=pr_number,
            quality_status=result.quality_status.value,
            success=result.success,
        )
    except Exception as e:
        logger.error(
            "Failed to trigger quality check",
            pr_number=pr_number,
            error=str(e),
        )


async def trigger_security_scan(
    session: AsyncSession,
    pr_number: int,
    pr_data: dict[str, Any],
) -> None:
    """
    Trigger security scan for a PR.
    
    Runs Bandit, Semgrep, and pip-audit in parallel, then posts
    results as a GitHub Check Run and PR comment.
    """
    try:
        from sdlc_agent.services.security_scanner import SecurityScanner
        from sdlc_agent.services.github_service import GitHubService
        from sdlc_agent.core.config import get_settings
        
        settings = get_settings()
        github = GitHubService(
            token=settings.github.token,
            owner=settings.github.owner,
            repo=settings.github.repo,
        )
        
        # Get PR files for targeted scanning
        pr_files = await github.get_pr_files(pr_number)
        
        # Run security scan
        scanner = SecurityScanner()
        result = await scanner.scan(files=pr_files, include_dependencies=True)
        
        # Post results as PR comment
        comment_body = result.to_markdown()
        await github.add_issue_comment(pr_number, comment_body)
        
        # Create GitHub Check Run for gate enforcement
        check_conclusion = "success" if result.passed else "failure"
        check_output = {
            "title": f"Security Scan: {result.security_score:.0f}/100",
            "summary": f"Found {result.critical_count} critical, {result.high_count} high, {result.medium_count} medium issues",
            "text": comment_body,
        }
        
        # Note: create_check_run requires GitHub App auth, falling back to status
        try:
            await github.create_commit_status(
                sha=pr_data.get("head", {}).get("sha", ""),
                state="success" if result.passed else "failure",
                context="security/scan",
                description=f"Score: {result.security_score:.0f}/100 - {len(result.sast_findings)} findings",
                target_url=None,
            )
        except Exception as status_error:
            logger.warning("Could not create commit status", error=str(status_error))
        
        logger.info(
            "Security scan completed",
            pr_number=pr_number,
            passed=result.passed,
            score=result.security_score,
            findings=len(result.sast_findings),
            vulns=len(result.dependency_vulnerabilities),
        )
        
    except Exception as e:
        logger.error(
            "Failed to trigger security scan",
            pr_number=pr_number,
            error=str(e),
        )
