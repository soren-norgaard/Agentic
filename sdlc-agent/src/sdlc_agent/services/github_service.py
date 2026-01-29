# =============================================================================
# SDLC Agent - GitHub Integration Service
# =============================================================================
"""
GitHub API integration for managing issues, PRs, and projects.
This service enables GitHub as the system of record for the SDLC.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)


class GitHubIssueState(str, Enum):
    """GitHub issue states."""
    OPEN = "open"
    CLOSED = "closed"


class GitHubLabel(str, Enum):
    """Standard SDLC labels for GitHub issues."""
    EPIC = "epic"
    FEATURE = "feature"
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    TECH_DEBT = "tech-debt"
    SPIKE = "spike"
    # Status labels
    NEEDS_DESIGN = "needs-design"
    NEEDS_ARCH = "needs-arch"
    READY_FOR_DEV = "ready-for-dev"
    IN_PROGRESS = "in-progress"
    IN_REVIEW = "in-review"
    BLOCKED = "blocked"
    # Priority labels
    PRIORITY_CRITICAL = "priority:critical"
    PRIORITY_HIGH = "priority:high"
    PRIORITY_MEDIUM = "priority:medium"
    PRIORITY_LOW = "priority:low"


@dataclass
class GitHubIssue:
    """GitHub Issue representation."""
    id: int
    number: int
    title: str
    body: str | None
    state: GitHubIssueState
    labels: list[str]
    assignees: list[str]
    milestone: str | None
    html_url: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


@dataclass
class GitHubPullRequest:
    """GitHub Pull Request representation."""
    id: int
    number: int
    title: str
    body: str | None
    state: str
    head_branch: str
    base_branch: str
    html_url: str
    draft: bool
    merged: bool
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None = None


@dataclass
class GitHubRepository:
    """GitHub Repository representation."""
    id: int
    name: str
    full_name: str
    description: str | None
    html_url: str
    clone_url: str
    default_branch: str
    private: bool


class GitHubService:
    """
    Service for interacting with GitHub API.
    
    Implements the "GitHub First" principle from the instruction file:
    - GitHub Issues = requirements, epics, tasks
    - GitHub Projects = portfolio & delivery tracking
    - Pull Requests = implementation & review
    """

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ):
        settings = get_settings()
        self.token = token or settings.github.token
        self.owner = owner or settings.github.owner
        self.repo = repo or settings.github.repo
        self.base_url = "https://api.github.com"
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # Repository Operations
    # =========================================================================

    async def get_repository(self, owner: str | None = None, repo: str | None = None) -> GitHubRepository:
        """Get repository information."""
        owner = owner or self.owner
        repo = repo or self.repo
        
        response = await self.client.get(f"/repos/{owner}/{repo}")
        response.raise_for_status()
        data = response.json()
        
        return GitHubRepository(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            description=data["description"],
            html_url=data["html_url"],
            clone_url=data["clone_url"],
            default_branch=data["default_branch"],
            private=data["private"],
        )

    # =========================================================================
    # Issue Operations
    # =========================================================================

    async def create_issue(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
    ) -> GitHubIssue:
        """
        Create a GitHub issue.
        
        This is the primary way to create work items in the "GitHub First" model.
        """
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone:
            payload["milestone"] = milestone

        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues",
            json=payload,
        )
        response.raise_for_status()
        return self._parse_issue(response.json())

    async def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: GitHubIssueState | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> GitHubIssue:
        """Update an existing GitHub issue."""
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state.value
        if labels is not None:
            payload["labels"] = labels
        if assignees is not None:
            payload["assignees"] = assignees

        response = await self.client.patch(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
            json=payload,
        )
        response.raise_for_status()
        return self._parse_issue(response.json())

    async def get_issue(self, issue_number: int) -> GitHubIssue:
        """Get a specific issue by number."""
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        )
        response.raise_for_status()
        return self._parse_issue(response.json())

    async def list_issues(
        self,
        state: GitHubIssueState = GitHubIssueState.OPEN,
        labels: list[str] | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubIssue]:
        """List issues with optional filters."""
        params: dict[str, Any] = {
            "state": state.value,
            "per_page": per_page,
            "page": page,
        }
        if labels:
            params["labels"] = ",".join(labels)

        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues",
            params=params,
        )
        response.raise_for_status()
        return [self._parse_issue(issue) for issue in response.json()]

    async def add_issue_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        """Add a comment to an issue."""
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    async def add_labels(self, issue_number: int, labels: list[str]) -> list[dict[str, Any]]:
        """Add labels to an issue."""
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/labels",
            json={"labels": labels},
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Pull Request Operations
    # =========================================================================

    async def create_pull_request(
        self,
        title: str,
        head: str,
        base: str,
        body: str | None = None,
        draft: bool = False,
    ) -> GitHubPullRequest:
        """Create a pull request."""
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }
        if body:
            payload["body"] = body

        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/pulls",
            json=payload,
        )
        response.raise_for_status()
        return self._parse_pull_request(response.json())

    async def get_pull_request(self, pr_number: int) -> GitHubPullRequest:
        """Get a specific pull request."""
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        )
        response.raise_for_status()
        return self._parse_pull_request(response.json())

    async def list_pull_requests(
        self,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubPullRequest]:
        """List pull requests."""
        params = {"state": state, "per_page": per_page, "page": page}
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls",
            params=params,
        )
        response.raise_for_status()
        return [self._parse_pull_request(pr) for pr in response.json()]

    async def add_pr_comment(self, pr_number: int, body: str) -> dict[str, Any]:
        """Add a comment to a pull request (uses issues API)."""
        return await self.add_issue_comment(pr_number, body)

    # =========================================================================
    # Branch Operations
    # =========================================================================

    async def create_branch(self, branch_name: str, from_branch: str | None = None) -> dict[str, Any]:
        """Create a new branch from an existing branch."""
        # Get the SHA of the source branch
        from_branch = from_branch or (await self.get_repository()).default_branch
        
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/git/refs/heads/{from_branch}"
        )
        response.raise_for_status()
        sha = response.json()["object"]["sha"]

        # Create the new branch
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/git/refs",
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            },
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Label Operations (for SDLC conventions)
    # =========================================================================

    async def ensure_labels_exist(self) -> list[dict[str, Any]]:
        """Ensure all SDLC labels exist in the repository."""
        label_configs = [
            # Issue types
            {"name": "epic", "color": "7057ff", "description": "Epic - large body of work"},
            {"name": "feature", "color": "0075ca", "description": "Feature request"},
            {"name": "story", "color": "0e8a16", "description": "User story"},
            {"name": "task", "color": "1d76db", "description": "Implementation task"},
            {"name": "bug", "color": "d73a4a", "description": "Bug report"},
            {"name": "tech-debt", "color": "fbca04", "description": "Technical debt"},
            {"name": "spike", "color": "f9d0c4", "description": "Research spike"},
            # Status labels
            {"name": "needs-design", "color": "c5def5", "description": "Needs UX/design review"},
            {"name": "needs-arch", "color": "d4c5f9", "description": "Needs architecture review"},
            {"name": "ready-for-dev", "color": "0e8a16", "description": "Ready for development"},
            {"name": "in-progress", "color": "fbca04", "description": "Work in progress"},
            {"name": "in-review", "color": "7057ff", "description": "In code review"},
            {"name": "blocked", "color": "b60205", "description": "Blocked by dependency"},
            # Priority labels
            {"name": "priority:critical", "color": "b60205", "description": "Critical priority"},
            {"name": "priority:high", "color": "d93f0b", "description": "High priority"},
            {"name": "priority:medium", "color": "fbca04", "description": "Medium priority"},
            {"name": "priority:low", "color": "0e8a16", "description": "Low priority"},
        ]

        created_labels = []
        for label in label_configs:
            try:
                response = await self.client.post(
                    f"/repos/{self.owner}/{self.repo}/labels",
                    json=label,
                )
                if response.status_code == 201:
                    created_labels.append(response.json())
                    logger.info(f"Created label: {label['name']}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    # Label already exists
                    logger.debug(f"Label already exists: {label['name']}")
                else:
                    logger.warning(f"Failed to create label {label['name']}: {e}")
        
        return created_labels

    # =========================================================================
    # SDLC-Specific Operations
    # =========================================================================

    async def create_epic(
        self,
        title: str,
        description: str,
        success_criteria: list[str] | None = None,
    ) -> GitHubIssue:
        """
        Create an Epic as a GitHub Issue.
        
        Per the instruction file:
        - Epics are GitHub Issues with 'epic' label
        - Must have business goal, scope, and success criteria
        """
        body_parts = [description]
        
        if success_criteria:
            body_parts.append("\n## Success Criteria")
            for criterion in success_criteria:
                body_parts.append(f"- [ ] {criterion}")
        
        body = "\n".join(body_parts)
        
        return await self.create_issue(
            title=title,
            body=body,
            labels=[GitHubLabel.EPIC.value, GitHubLabel.NEEDS_ARCH.value],
        )

    async def create_story(
        self,
        title: str,
        as_a: str,
        i_want: str,
        so_that: str,
        acceptance_criteria: list[dict[str, str]] | None = None,
        epic_number: int | None = None,
    ) -> GitHubIssue:
        """
        Create a User Story as a GitHub Issue.
        
        Per the instruction file:
        - Stories use Gherkin-style acceptance criteria
        - Must be INVEST-compliant
        """
        body_parts = [
            f"**As a** {as_a}",
            f"**I want** {i_want}",
            f"**So that** {so_that}",
        ]
        
        if epic_number:
            body_parts.insert(0, f"Epic: #{epic_number}\n")
        
        if acceptance_criteria:
            body_parts.append("\n## Acceptance Criteria")
            for ac in acceptance_criteria:
                body_parts.append(f"\n### {ac.get('scenario', 'Scenario')}")
                if 'given' in ac:
                    body_parts.append(f"**Given** {ac['given']}")
                if 'when' in ac:
                    body_parts.append(f"**When** {ac['when']}")
                if 'then' in ac:
                    body_parts.append(f"**Then** {ac['then']}")
        
        body = "\n".join(body_parts)
        
        return await self.create_issue(
            title=title,
            body=body,
            labels=[GitHubLabel.STORY.value, GitHubLabel.NEEDS_DESIGN.value],
        )

    async def create_task(
        self,
        title: str,
        description: str,
        story_number: int | None = None,
        skills_required: list[str] | None = None,
        story_points: int | None = None,
    ) -> GitHubIssue:
        """Create a Task as a GitHub Issue."""
        body_parts = [description]
        
        if story_number:
            body_parts.insert(0, f"Story: #{story_number}\n")
        
        if story_points:
            body_parts.append(f"\n**Story Points:** {story_points}")
        
        if skills_required:
            body_parts.append(f"\n**Skills Required:** {', '.join(skills_required)}")
        
        body = "\n".join(body_parts)
        
        return await self.create_issue(
            title=title,
            body=body,
            labels=[GitHubLabel.TASK.value],
        )

    async def transition_to_ready_for_dev(self, issue_number: int) -> GitHubIssue:
        """Mark an issue as ready for development (DoD met)."""
        issue = await self.get_issue(issue_number)
        
        # Remove status labels and add ready-for-dev
        new_labels = [
            l for l in issue.labels 
            if l not in ["needs-design", "needs-arch", "blocked"]
        ]
        new_labels.append(GitHubLabel.READY_FOR_DEV.value)
        
        return await self.update_issue(issue_number, labels=new_labels)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_issue(self, data: dict[str, Any]) -> GitHubIssue:
        """Parse GitHub API response into GitHubIssue."""
        return GitHubIssue(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=GitHubIssueState(data["state"]),
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[user["login"] for user in data.get("assignees", [])],
            milestone=data.get("milestone", {}).get("title") if data.get("milestone") else None,
            html_url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00")) if data.get("closed_at") else None,
        )

    def _parse_pull_request(self, data: dict[str, Any]) -> GitHubPullRequest:
        """Parse GitHub API response into GitHubPullRequest."""
        return GitHubPullRequest(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            html_url=data["html_url"],
            draft=data.get("draft", False),
            merged=data.get("merged", False),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            merged_at=datetime.fromisoformat(data["merged_at"].replace("Z", "+00:00")) if data.get("merged_at") else None,
        )


# Singleton instance
_github_service: GitHubService | None = None


def get_github_service() -> GitHubService:
    """Get or create the GitHub service singleton."""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service
