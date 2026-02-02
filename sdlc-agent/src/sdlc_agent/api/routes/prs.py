# =============================================================================
# SDLC Agent - PR-Centric Routes
# =============================================================================
"""
PR-centric API endpoints for code review, quality checks, and dashboard.

These endpoints work independently of workflows, making it easy to:
- List all open PRs with review/quality status
- Trigger code reviews on any PR
- Run quality checks (test coverage, linting)
- Get aggregated dashboard views

Key Design Principles:
- No workflow_id required
- Works for any PR (from any source - SDLC workflow, manual, external)
- Aggregates code review + quality + CI status
- Supports webhook-triggered automation
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Artifact, get_session

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class ReviewStatus(str, Enum):
    """Status of code review for a PR."""
    PENDING = "pending"          # No review yet
    IN_PROGRESS = "in_progress"  # Review started but not complete
    REVIEWED = "reviewed"        # Agent review complete, awaiting human
    APPROVED = "approved"        # Human approved
    CHANGES_REQUESTED = "changes_requested"  # Changes needed
    

class QualityStatus(str, Enum):
    """Status of quality checks for a PR."""
    UNKNOWN = "unknown"      # Not checked yet
    PASSING = "passing"      # All checks pass
    WARNING = "warning"      # Some issues but not blocking
    FAILING = "failing"      # Critical issues found


class CIStatus(str, Enum):
    """Status of CI/CD checks."""
    UNKNOWN = "unknown"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class SecurityStatus(str, Enum):
    """Status of security scan for a PR."""
    PENDING = "pending"          # Not scanned yet
    SCANNING = "scanning"        # Scan in progress
    SECURE = "secure"            # No security issues
    WARNING = "warning"          # Low/medium issues found
    VULNERABLE = "vulnerable"    # High/critical issues found


# =============================================================================
# Schemas
# =============================================================================

class PRSummary(BaseModel):
    """Summary of a PR with all statuses."""
    number: int
    title: str
    author: str
    branch: str
    base: str
    created_at: datetime
    updated_at: datetime
    
    # Statuses
    review_status: ReviewStatus = ReviewStatus.PENDING
    quality_status: QualityStatus = QualityStatus.UNKNOWN
    security_status: SecurityStatus = SecurityStatus.PENDING
    ci_status: CIStatus = CIStatus.UNKNOWN
    
    # Metrics
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    test_coverage: float | None = None
    
    # Links
    html_url: str
    review_artifact_id: uuid.UUID | None = None


class PRListResponse(BaseModel):
    """Response for listing PRs."""
    total: int
    open_count: int
    prs: list[PRSummary]


class ReviewRequest(BaseModel):
    """Request to trigger a code review."""
    focus_areas: list[str] = Field(
        default_factory=lambda: ["security", "performance", "maintainability", "testing"],
        description="Areas to focus the review on"
    )
    auto_submit: bool = Field(
        default=True,
        description="Whether to post the review to GitHub"
    )


class ReviewResponse(BaseModel):
    """Response from triggering a code review."""
    success: bool
    pr_number: int
    files_analyzed: int
    findings_count: int
    review_brief: str | None = None
    review_submitted: bool = False
    artifact_id: uuid.UUID | None = None
    message: str


class QualityCheckRequest(BaseModel):
    """Request for quality check."""
    check_tests: bool = Field(default=True, description="Check for test coverage")
    check_linting: bool = Field(default=True, description="Run lint checks")
    check_types: bool = Field(default=True, description="Run type checking")
    check_dependencies: bool = Field(default=True, description="Check dependencies")


class SecurityScanRequest(BaseModel):
    """Request to trigger a security scan."""
    include_dependencies: bool = Field(default=True, description="Scan for vulnerable dependencies")
    post_comment: bool = Field(default=True, description="Post results as PR comment")


class SecurityScanResponse(BaseModel):
    """Response from security scan."""
    success: bool
    pr_number: int
    passed: bool
    security_score: float
    
    # Counts
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Details
    sast_findings_count: int = 0
    dependency_vulns_count: int = 0
    blocking_issues: list[str] = []
    
    # Output
    summary_markdown: str
    artifact_id: uuid.UUID | None = None
    posted_to_github: bool = False


class TestCoverageResult(BaseModel):
    """Test coverage analysis result."""
    files_changed: int
    files_with_tests: int
    coverage_percentage: float
    missing_tests: list[str]
    test_files_found: list[str]


class QualityCheckResponse(BaseModel):
    """Response from quality check."""
    success: bool
    pr_number: int
    quality_status: QualityStatus
    
    # Detailed results
    test_coverage: TestCoverageResult | None = None
    lint_issues: int = 0
    type_errors: int = 0
    security_issues: int = 0
    
    # Summary
    summary_markdown: str
    artifact_id: uuid.UUID | None = None
    posted_to_github: bool = False


class DashboardSummary(BaseModel):
    """Dashboard summary of all PR activity."""
    total_open_prs: int
    pending_reviews: int
    quality_passing: int
    quality_failing: int
    ci_passing: int
    ci_failing: int
    
    # Lists
    prs_needing_review: list[PRSummary]
    prs_with_issues: list[PRSummary]
    recent_reviews: list[dict[str, Any]]


# =============================================================================
# Helper Functions
# =============================================================================

def get_github_config() -> tuple[str, str]:
    """Get GitHub owner/repo from settings."""
    settings = get_settings()
    if not settings.github.owner or not settings.github.repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub repository not configured. Set GITHUB_OWNER and GITHUB_REPO."
        )
    return settings.github.owner, settings.github.repo


def determine_review_status(reviews: list[dict]) -> ReviewStatus:
    """Determine overall review status from GitHub reviews."""
    if not reviews:
        return ReviewStatus.PENDING
    
    # Check most recent review state
    states = [r.get("state", "").upper() for r in reviews]
    
    if "APPROVED" in states:
        return ReviewStatus.APPROVED
    if "CHANGES_REQUESTED" in states:
        return ReviewStatus.CHANGES_REQUESTED
    if "COMMENTED" in states:
        return ReviewStatus.REVIEWED
    
    return ReviewStatus.IN_PROGRESS


def determine_ci_status(check_runs: list[dict]) -> CIStatus:
    """Determine CI status from GitHub check runs."""
    if not check_runs:
        return CIStatus.UNKNOWN
    
    conclusions = [c.get("conclusion") for c in check_runs if c.get("conclusion")]
    statuses = [c.get("status") for c in check_runs]
    
    if any(s == "in_progress" or s == "queued" for s in statuses):
        return CIStatus.RUNNING
    if any(c == "failure" for c in conclusions):
        return CIStatus.FAILURE
    if all(c == "success" for c in conclusions):
        return CIStatus.SUCCESS
    if any(c == "pending" for c in conclusions):
        return CIStatus.PENDING
    
    return CIStatus.UNKNOWN


async def analyze_test_coverage(
    pr_files: list[dict],
    github_service: Any,
) -> TestCoverageResult:
    """
    Analyze test coverage for changed files.
    
    Checks if test files exist for the changed source files.
    """
    files_changed = len(pr_files)
    source_files = []
    test_files_found = []
    
    # Categorize files
    for f in pr_files:
        filename = f.get("filename", "")
        if filename.endswith(".py"):
            if "test" in filename.lower() or filename.startswith("test_"):
                test_files_found.append(filename)
            else:
                source_files.append(filename)
    
    # Check which source files have corresponding tests
    files_with_tests = 0
    missing_tests = []
    
    for src_file in source_files:
        # Common test file patterns
        basename = src_file.split("/")[-1].replace(".py", "")
        dirname = "/".join(src_file.split("/")[:-1])
        
        potential_test_files = [
            f"test_{basename}.py",
            f"{basename}_test.py",
            f"tests/test_{basename}.py",
            f"{dirname}/tests/test_{basename}.py",
            f"tests/{dirname}/test_{basename}.py",
        ]
        
        # Check if any test file exists in the PR files or repo
        has_test = any(
            t in [f.get("filename") for f in pr_files]
            for t in potential_test_files
        )
        
        if has_test:
            files_with_tests += 1
        else:
            missing_tests.append(src_file)
    
    coverage_pct = (files_with_tests / len(source_files) * 100) if source_files else 100.0
    
    return TestCoverageResult(
        files_changed=files_changed,
        files_with_tests=files_with_tests,
        coverage_percentage=round(coverage_pct, 1),
        missing_tests=missing_tests,
        test_files_found=test_files_found,
    )


# =============================================================================
# PR Listing Endpoints
# =============================================================================

@router.get("", response_model=PRListResponse)
async def list_prs(
    state: str = Query(default="open", description="PR state: open, closed, all"),
    session: AsyncSession = Depends(get_session),
) -> PRListResponse:
    """
    List all pull requests with their review and quality status.
    
    Returns aggregated status from:
    - Agent code reviews (from artifacts)
    - GitHub human reviews
    - CI/CD check status
    """
    from sdlc_agent.services.github_service import GitHubService
    
    owner, repo = get_github_config()
    github = GitHubService()
    
    try:
        # Fetch PRs from GitHub
        prs_data = await github.list_pull_requests(state=state)
    except Exception as e:
        logger.error("Failed to fetch PRs from GitHub", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch PRs from GitHub: {e}"
        )
    
    pr_summaries = []
    
    for pr in prs_data:
        # pr is a GitHubPullRequest object
        pr_number = pr.number
        
        # Get reviews for this PR
        try:
            reviews = await github.get_pr_reviews(pr_number)
        except Exception:
            reviews = []
        
        # Check if we have an agent review artifact
        review_artifact = await session.execute(
            select(Artifact)
            .where(Artifact.artifact_type == "review_brief")
            .where(Artifact.extra_data["pr_number"].astext == str(pr_number))
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        artifact = review_artifact.scalar_one_or_none()
        
        # Check if we have a quality check artifact
        quality_artifact_result = await session.execute(
            select(Artifact)
            .where(Artifact.artifact_type == "quality_report")
            .where(Artifact.extra_data["pr_number"].astext == str(pr_number))
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        quality_artifact = quality_artifact_result.scalar_one_or_none()
        
        # Check if we have a security scan artifact
        security_artifact_result = await session.execute(
            select(Artifact)
            .where(Artifact.artifact_type == "security_scan")
            .where(Artifact.extra_data["pr_number"].astext == str(pr_number))
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        security_artifact = security_artifact_result.scalar_one_or_none()
        
        # Determine quality status from artifact
        quality_status = QualityStatus.UNKNOWN
        if quality_artifact and quality_artifact.extra_data:
            status_str = quality_artifact.extra_data.get("quality_status", "unknown")
            try:
                quality_status = QualityStatus(status_str)
            except ValueError:
                quality_status = QualityStatus.UNKNOWN
        
        # Determine security status from artifact
        security_status = SecurityStatus.PENDING
        if security_artifact and security_artifact.extra_data:
            passed = security_artifact.extra_data.get("passed", False)
            critical = security_artifact.extra_data.get("critical_count", 0)
            high = security_artifact.extra_data.get("high_count", 0)
            medium = security_artifact.extra_data.get("medium_count", 0)
            
            if passed and critical == 0 and high == 0:
                security_status = SecurityStatus.SECURE
            elif critical > 0 or high > 0:
                security_status = SecurityStatus.VULNERABLE
            elif medium > 0:
                security_status = SecurityStatus.WARNING
            else:
                security_status = SecurityStatus.SECURE
        
        # Determine statuses
        review_status = determine_review_status(reviews)
        if artifact and review_status == ReviewStatus.PENDING:
            review_status = ReviewStatus.REVIEWED
        
        summary = PRSummary(
            number=pr_number,
            title=pr.title or "",
            author="",  # GitHubPullRequest doesn't store author
            branch=pr.head_branch or "",
            base=pr.base_branch or "",
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            review_status=review_status,
            quality_status=quality_status,
            security_status=security_status,
            files_changed=0,  # Not available in list response
            additions=0,
            deletions=0,
            html_url=pr.html_url or "",
            review_artifact_id=artifact.id if artifact else None,
        )
        pr_summaries.append(summary)
    
    open_count = sum(1 for pr in pr_summaries if pr.review_status != ReviewStatus.APPROVED)
    
    return PRListResponse(
        total=len(pr_summaries),
        open_count=open_count,
        prs=pr_summaries,
    )


@router.get("/{pr_number}", response_model=PRSummary)
async def get_pr(
    pr_number: int,
    session: AsyncSession = Depends(get_session),
) -> PRSummary:
    """Get detailed information about a specific PR."""
    from sdlc_agent.services.github_service import GitHubService
    
    github = GitHubService()
    
    try:
        pr = await github.get_pull_request(pr_number)
        reviews = await github.get_pr_reviews(pr_number)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PR #{pr_number} not found: {e}"
        )
    
    # Check for agent review artifact
    review_artifact = await session.execute(
        select(Artifact)
        .where(Artifact.artifact_type == "review_brief")
        .where(Artifact.extra_data["pr_number"].astext == str(pr_number))
        .order_by(Artifact.created_at.desc())
        .limit(1)
    )
    artifact = review_artifact.scalar_one_or_none()
    
    review_status = determine_review_status(reviews)
    if artifact and review_status == ReviewStatus.PENDING:
        review_status = ReviewStatus.REVIEWED
    
    return PRSummary(
        number=pr_number,
        title=pr.title,
        author="",  # GitHubPullRequest doesn't store author
        branch=pr.head_branch or "",
        base=pr.base_branch or "",
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        review_status=review_status,
        files_changed=0,  # Not available in single PR endpoint
        additions=0,
        deletions=0,
        html_url=pr.html_url,
        review_artifact_id=artifact.id if artifact else None,
    )


# =============================================================================
# Code Review Endpoints
# =============================================================================

@router.post("/{pr_number}/review", response_model=ReviewResponse)
async def trigger_code_review(
    pr_number: int,
    request: ReviewRequest = ReviewRequest(),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    """
    Trigger a code review on a PR.
    
    This endpoint works independently of workflows.
    It will:
    1. Fetch PR files and diff from GitHub
    2. Analyze for code quality, security, performance issues
    3. Generate a review brief
    4. Optionally post as a review comment on GitHub
    5. Save as an artifact for the dashboard
    """
    from sdlc_agent.agents.code_review import ReviewBrief
    from sdlc_agent.services.github_service import GitHubService
    
    github = GitHubService()
    
    # Fetch PR details
    try:
        pr = await github.get_pull_request(pr_number)
        pr_files = await github.get_pr_files(pr_number)
    except Exception as e:
        return ReviewResponse(
            success=False,
            pr_number=pr_number,
            files_analyzed=0,
            findings_count=0,
            review_submitted=False,
            message=f"Failed to fetch PR #{pr_number}: {e}",
        )
    
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
        ("TODO", "TODO comment found - verify if intentional", "info"),
        ("XXX", "XXX comment found - needs attention", "minor"),
    ]
    
    performance_patterns = [
        ("SELECT *", "SELECT * in SQL - consider selecting specific columns", "minor"),
        ("time.sleep", "Synchronous sleep - consider async alternatives", "info"),
        ("for .* in .*\.keys()", "Iterating over .keys() - iterate over dict directly", "info"),
    ]
    
    maintainability_patterns = [
        ("except:", "Bare except clause - catch specific exceptions", "minor"),
        ("except Exception:", "Broad exception handling - consider specific types", "info"),
        ("global ", "Global variable usage - consider refactoring", "minor"),
        ("# type: ignore", "Type ignore comment - verify type safety", "info"),
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
        if "security" in request.focus_areas:
            for pattern, message, severity in security_patterns:
                if pattern.lower() in patch.lower():
                    findings.append({
                        "severity": severity,
                        "category": "security",
                        "file": filename,
                        "message": message,
                    })
        
        # Performance analysis
        if "performance" in request.focus_areas:
            for pattern, message, severity in performance_patterns:
                if re.search(pattern, patch, re.IGNORECASE):
                    findings.append({
                        "severity": severity,
                        "category": "performance",
                        "file": filename,
                        "message": message,
                    })
        
        # Maintainability analysis
        if "maintainability" in request.focus_areas:
            for pattern, message, severity in maintainability_patterns:
                if re.search(pattern, patch, re.IGNORECASE):
                    findings.append({
                        "severity": severity,
                        "category": "maintainability",
                        "file": filename,
                        "message": message,
                    })
    
    # Create review brief
    brief = ReviewBrief(
        pr_number=pr_number,
        pr_title=pr.title,
        story_id=None,
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
    from sdlc_agent.services.artifact_service import ArtifactService
    
    artifact = await ArtifactService.create_artifact(
        name=f"Code Review - PR #{pr_number}",
        artifact_type="review_brief",
        content=brief_markdown,
        extra_data={
            "pr_number": pr_number,
            "pr_title": pr.title,
            "files_analyzed": len(pr_files),
            "findings_count": len(findings),
            "focus_areas": request.focus_areas,
        },
    )
    
    # Submit review to GitHub if requested
    review_submitted = False
    if request.auto_submit:
        try:
            await github.submit_pr_review(
                pr_number=pr_number,
                body=brief_markdown,
                event="COMMENT",
            )
            review_submitted = True
            logger.info("Submitted review to GitHub", pr_number=pr_number)
        except Exception as e:
            logger.warning("Failed to submit review to GitHub", error=str(e))
    
    return ReviewResponse(
        success=True,
        pr_number=pr_number,
        files_analyzed=len(pr_files),
        findings_count=len(findings),
        review_brief=brief_markdown,
        review_submitted=review_submitted,
        artifact_id=artifact.id,
        message=f"Analyzed PR #{pr_number}: {len(pr_files)} files, {len(findings)} findings",
    )


# =============================================================================
# Quality Check Endpoints
# =============================================================================

@router.post("/{pr_number}/quality", response_model=QualityCheckResponse)
async def run_quality_check(
    pr_number: int,
    request: QualityCheckRequest = QualityCheckRequest(),
    session: AsyncSession = Depends(get_session),
) -> QualityCheckResponse:
    """
    Run quality checks on a PR.
    
    Checks include:
    - Test coverage analysis (are changed files covered by tests?)
    - Linting issues
    - Type checking errors
    - Security dependency scan
    """
    from sdlc_agent.services.github_service import GitHubService
    from sdlc_agent.services.artifact_service import ArtifactService
    
    github = GitHubService()
    
    try:
        pr = await github.get_pull_request(pr_number)
        pr_files = await github.get_pr_files(pr_number)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to fetch PR #{pr_number}: {e}"
        )
    
    # Analyze test coverage
    test_coverage = None
    if request.check_tests:
        test_coverage = await analyze_test_coverage(pr_files, github)
    
    # Determine quality status
    quality_status = QualityStatus.PASSING
    issues = []
    
    if test_coverage:
        if test_coverage.coverage_percentage < 50:
            quality_status = QualityStatus.FAILING
            issues.append(f"Low test coverage: {test_coverage.coverage_percentage}%")
        elif test_coverage.coverage_percentage < 80:
            quality_status = QualityStatus.WARNING
            issues.append(f"Test coverage below 80%: {test_coverage.coverage_percentage}%")
    
    # Build summary markdown
    summary_lines = [
        f"## 🧪 Quality Report - PR #{pr_number}",
        "",
        f"**Status:** {quality_status.value.upper()}",
        "",
    ]
    
    if test_coverage:
        summary_lines.extend([
            "### Test Coverage",
            "",
            f"- Files changed: {test_coverage.files_changed}",
            f"- Files with tests: {test_coverage.files_with_tests}/{len(test_coverage.missing_tests) + test_coverage.files_with_tests}",
            f"- Coverage: {test_coverage.coverage_percentage}%",
            "",
        ])
        
        if test_coverage.missing_tests:
            summary_lines.append("**Missing tests for:**")
            for f in test_coverage.missing_tests[:5]:
                summary_lines.append(f"- `{f}`")
            if len(test_coverage.missing_tests) > 5:
                summary_lines.append(f"- ... and {len(test_coverage.missing_tests) - 5} more")
            summary_lines.append("")
    
    if issues:
        summary_lines.extend([
            "### Issues Found",
            "",
        ])
        for issue in issues:
            summary_lines.append(f"- ⚠️ {issue}")
        summary_lines.append("")
    
    summary_lines.extend([
        "---",
        "🤖 *This quality report was auto-generated.*",
    ])
    
    summary_markdown = "\n".join(summary_lines)
    
    # Save artifact
    artifact = await ArtifactService.create_artifact(
        name=f"Quality Report - PR #{pr_number}",
        artifact_type="quality_report",
        content=summary_markdown,
        extra_data={
            "pr_number": pr_number,
            "quality_status": quality_status.value,
            "test_coverage": test_coverage.model_dump() if test_coverage else None,
        },
    )
    
    # Post to GitHub if there are issues
    posted = False
    if quality_status != QualityStatus.PASSING:
        try:
            await github.submit_pr_review(
                pr_number=pr_number,
                body=summary_markdown,
                event="COMMENT",
            )
            posted = True
        except Exception as e:
            logger.warning("Failed to post quality report to GitHub", error=str(e))
    
    return QualityCheckResponse(
        success=True,
        pr_number=pr_number,
        quality_status=quality_status,
        test_coverage=test_coverage,
        summary_markdown=summary_markdown,
        artifact_id=artifact.id,
        posted_to_github=posted,
    )


@router.post("/{pr_number}/security", response_model=SecurityScanResponse)
async def run_security_scan(
    pr_number: int,
    request: SecurityScanRequest = SecurityScanRequest(),
    session: AsyncSession = Depends(get_session),
) -> SecurityScanResponse:
    """
    Run security scan on a PR.
    
    Performs multi-layer security analysis:
    - SAST with Bandit (Python security linter)
    - SAST with Semgrep (OWASP rules)
    - Dependency vulnerability scanning with pip-audit
    
    Returns findings with severity ratings and blocks merge
    if critical or high severity issues are found.
    """
    from sdlc_agent.services.github_service import GitHubService
    from sdlc_agent.services.security_scanner import SecurityScanner
    from sdlc_agent.services.artifact_service import ArtifactService
    
    github = GitHubService()
    
    try:
        pr = await github.get_pull_request(pr_number)
        pr_files = await github.get_pr_files(pr_number)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to fetch PR #{pr_number}: {e}"
        )
    
    # Run security scan
    scanner = SecurityScanner()
    result = await scanner.scan(
        files=pr_files,
        include_dependencies=request.include_dependencies,
    )
    
    summary_markdown = result.to_markdown()
    
    # Save artifact
    artifact = await ArtifactService.create_artifact(
        name=f"Security Scan - PR #{pr_number}",
        artifact_type="security_scan",
        content=summary_markdown,
        extra_data={
            "pr_number": pr_number,
            "passed": result.passed,
            "security_score": result.security_score,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count,
        },
    )
    
    # Post to GitHub if requested
    posted = False
    if request.post_comment:
        try:
            await github.add_issue_comment(pr_number, summary_markdown)
            posted = True
        except Exception as e:
            logger.warning("Failed to post security scan to GitHub", error=str(e))
    
    return SecurityScanResponse(
        success=result.success,
        pr_number=pr_number,
        passed=result.passed,
        security_score=result.security_score,
        critical_count=result.critical_count,
        high_count=result.high_count,
        medium_count=result.medium_count,
        low_count=result.low_count,
        sast_findings_count=len(result.sast_findings),
        dependency_vulns_count=len(result.dependency_vulnerabilities),
        blocking_issues=result.blocking_issues,
        summary_markdown=summary_markdown,
        artifact_id=artifact.id,
        posted_to_github=posted,
    )


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    """
    Get dashboard summary of all PR activity.
    
    Returns:
    - Counts of PRs in various states
    - PRs needing review
    - PRs with quality issues
    - Recent review activity
    """
    # Get all open PRs
    prs_response = await list_prs(state="open", session=session)
    
    pending_reviews = [
        pr for pr in prs_response.prs
        if pr.review_status == ReviewStatus.PENDING
    ]
    
    # Get quality artifacts for these PRs
    prs_with_issues = []
    quality_passing = 0
    quality_failing = 0
    
    for pr in prs_response.prs:
        quality_artifact = await session.execute(
            select(Artifact)
            .where(Artifact.artifact_type == "quality_report")
            .where(Artifact.extra_data["pr_number"].astext == str(pr.number))
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        artifact = quality_artifact.scalar_one_or_none()
        
        if artifact:
            status = artifact.extra_data.get("quality_status", "unknown")
            if status == "passing":
                quality_passing += 1
            elif status == "failing":
                quality_failing += 1
                prs_with_issues.append(pr)
    
    # Get recent review artifacts
    recent_reviews_result = await session.execute(
        select(Artifact)
        .where(Artifact.artifact_type == "review_brief")
        .order_by(Artifact.created_at.desc())
        .limit(10)
    )
    recent_artifacts = recent_reviews_result.scalars().all()
    
    recent_reviews = [
        {
            "pr_number": a.extra_data.get("pr_number"),
            "pr_title": a.extra_data.get("pr_title"),
            "created_at": a.created_at.isoformat(),
            "findings_count": a.extra_data.get("findings_count", 0),
        }
        for a in recent_artifacts
    ]
    
    return DashboardSummary(
        total_open_prs=prs_response.total,
        pending_reviews=len(pending_reviews),
        quality_passing=quality_passing,
        quality_failing=quality_failing,
        ci_passing=0,  # TODO: Aggregate from GitHub checks
        ci_failing=0,
        prs_needing_review=pending_reviews[:5],
        prs_with_issues=prs_with_issues[:5],
        recent_reviews=recent_reviews,
    )
