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


@dataclass
class GitHubProjectField:
    """GitHub Project v2 field."""
    id: str
    name: str
    field_type: str  # "single_select", "text", "number", "date", "iteration"
    options: list[dict[str, str]] | None = None  # For single_select fields


@dataclass
class GitHubProject:
    """GitHub Project v2 representation."""
    id: str  # Node ID for GraphQL
    number: int
    title: str
    url: str
    fields: list[GitHubProjectField] | None = None


@dataclass
class GitHubProjectItem:
    """An item (issue/PR) in a GitHub Project."""
    id: str  # Project item ID
    content_id: str  # Issue/PR node ID
    content_type: str  # "Issue" or "PullRequest"


class GitHubService:
    """
    Service for interacting with GitHub API.
    
    Implements the "GitHub First" principle from the instruction file:
    - GitHub Issues = requirements, epics, tasks
    - GitHub Projects = portfolio & delivery tracking
    - Pull Requests = implementation & review
    """

    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ):
        settings = get_settings()
        # Handle SecretStr - need to call get_secret_value()
        github_token = settings.github.token
        if github_token is not None and hasattr(github_token, 'get_secret_value'):
            github_token = github_token.get_secret_value()
        self.token = token or github_token
        self.owner = owner or settings.github.owner
        self.repo = repo or settings.github.repo
        self.base_url = "https://api.github.com"
        self._client: httpx.AsyncClient | None = None
        # Cache for project info to avoid repeated lookups
        self._project_cache: dict[str, GitHubProject] = {}
        self._owner_node_id: str | None = None

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
    # GraphQL Operations
    # =========================================================================

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query against GitHub API."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.client.post(
            self.GRAPHQL_URL,
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            error_messages = [e.get("message", str(e)) for e in result["errors"]]
            raise Exception(f"GraphQL errors: {'; '.join(error_messages)}")
        
        return result.get("data", {})

    async def _get_owner_node_id(self) -> str:
        """Get the node ID for the repository owner (user or org)."""
        if self._owner_node_id:
            return self._owner_node_id

        # Try as organization first
        query = """
        query($login: String!) {
            organization(login: $login) {
                id
            }
        }
        """
        try:
            data = await self._graphql(query, {"login": self.owner})
            if data.get("organization"):
                self._owner_node_id = data["organization"]["id"]
                return self._owner_node_id
        except Exception:
            pass

        # Fall back to user
        query = """
        query($login: String!) {
            user(login: $login) {
                id
            }
        }
        """
        data = await self._graphql(query, {"login": self.owner})
        self._owner_node_id = data["user"]["id"]
        return self._owner_node_id

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

    async def get_file_content(
        self,
        path: str,
        ref: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ) -> dict[str, Any]:
        """
        Get the contents of a file from the repository.
        
        Args:
            path: Path to the file in the repository
            ref: Branch, tag, or commit SHA (defaults to default branch)
            owner: Repository owner (defaults to configured owner)
            repo: Repository name (defaults to configured repo)
            
        Returns:
            Dictionary with 'content' (decoded), 'sha', 'size', 'path', 'encoding'
        """
        import base64
        
        owner = owner or self.owner
        repo = repo or self.repo
        
        params = {}
        if ref:
            params["ref"] = ref
            
        response = await self.client.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle file vs directory
        if isinstance(data, list):
            raise ValueError(f"Path '{path}' is a directory, not a file")
        
        # Decode base64 content
        content = ""
        if data.get("content") and data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8")
        
        return {
            "path": data["path"],
            "sha": data["sha"],
            "size": data["size"],
            "content": content,
            "encoding": data.get("encoding"),
            "html_url": data.get("html_url"),
        }

    async def get_directory_contents(
        self,
        path: str = "",
        ref: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get the contents of a directory from the repository.
        
        Args:
            path: Path to the directory (empty string for root)
            ref: Branch, tag, or commit SHA (defaults to default branch)
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of items with 'name', 'path', 'type' ('file' or 'dir'), 'sha', 'size'
        """
        owner = owner or self.owner
        repo = repo or self.repo
        
        params = {}
        if ref:
            params["ref"] = ref
            
        response = await self.client.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle single file response
        if isinstance(data, dict):
            return [data]
        
        return [
            {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],  # 'file' or 'dir'
                "sha": item["sha"],
                "size": item.get("size", 0),
                "html_url": item.get("html_url"),
            }
            for item in data
        ]

    async def get_tree(
        self,
        ref: str | None = None,
        recursive: bool = True,
        owner: str | None = None,
        repo: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get the full file tree of the repository.
        
        Args:
            ref: Branch, tag, or commit SHA (defaults to default branch)
            recursive: Whether to get all files recursively
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of all files/directories with 'path', 'type', 'sha', 'size'
        """
        owner = owner or self.owner
        repo = repo or self.repo
        
        # Get the default branch if ref not specified
        if not ref:
            repo_info = await self.get_repository(owner, repo)
            ref = repo_info.default_branch
        
        # Get the tree SHA for the ref
        response = await self.client.get(
            f"/repos/{owner}/{repo}/git/ref/heads/{ref}"
        )
        response.raise_for_status()
        commit_sha = response.json()["object"]["sha"]
        
        # Get commit to find tree SHA
        response = await self.client.get(
            f"/repos/{owner}/{repo}/git/commits/{commit_sha}"
        )
        response.raise_for_status()
        tree_sha = response.json()["tree"]["sha"]
        
        # Get the tree
        params = {"recursive": "1"} if recursive else {}
        response = await self.client.get(
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            params=params,
        )
        response.raise_for_status()
        tree_data = response.json()
        
        return [
            {
                "path": item["path"],
                "type": "file" if item["type"] == "blob" else "dir",
                "sha": item["sha"],
                "size": item.get("size", 0),
                "mode": item.get("mode"),
            }
            for item in tree_data.get("tree", [])
        ]

    async def search_code(
        self,
        query: str,
        owner: str | None = None,
        repo: str | None = None,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Search for code in the repository.
        
        Args:
            query: Search query (supports GitHub code search syntax)
            owner: Repository owner
            repo: Repository name
            per_page: Number of results per page (max 100)
            
        Returns:
            List of matching files with 'path', 'sha', 'html_url', 'text_matches'
        """
        owner = owner or self.owner
        repo = repo or self.repo
        
        # Build the search query with repo qualifier
        full_query = f"{query} repo:{owner}/{repo}"
        
        response = await self.client.get(
            "/search/code",
            params={
                "q": full_query,
                "per_page": min(per_page, 100),
            },
            headers={
                **self.client.headers,
                "Accept": "application/vnd.github.text-match+json",
            },
        )
        response.raise_for_status()
        data = response.json()
        
        return [
            {
                "name": item["name"],
                "path": item["path"],
                "sha": item["sha"],
                "html_url": item["html_url"],
                "repository": item["repository"]["full_name"],
                "text_matches": item.get("text_matches", []),
            }
            for item in data.get("items", [])
        ]

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

    async def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get the list of files changed in a pull request.
        
        Returns list of dicts with:
        - filename: Path to the file
        - status: added, removed, modified, renamed, copied, changed
        - additions: Number of lines added
        - deletions: Number of lines deleted
        - changes: Total changes
        - patch: The actual diff patch (if available)
        """
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        response.raise_for_status()
        
        files = []
        for f in response.json():
            files.append({
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "changes": f.get("changes", 0),
                "patch": f.get("patch"),
                "blob_url": f.get("blob_url"),
                "raw_url": f.get("raw_url"),
                "contents_url": f.get("contents_url"),
                "previous_filename": f.get("previous_filename"),
            })
        return files

    async def get_pr_diff(self, pr_number: int) -> str:
        """
        Get the full diff of a pull request as a unified diff string.
        
        This returns the raw diff output that can be parsed for code review.
        """
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        response.raise_for_status()
        return response.text

    async def get_pr_commits(self, pr_number: int) -> list[dict[str, Any]]:
        """Get the list of commits in a pull request."""
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/commits",
            params={"per_page": 100},
        )
        response.raise_for_status()
        
        commits = []
        for c in response.json():
            commits.append({
                "sha": c.get("sha"),
                "message": c.get("commit", {}).get("message"),
                "author": c.get("commit", {}).get("author", {}).get("name"),
                "date": c.get("commit", {}).get("author", {}).get("date"),
            })
        return commits

    async def submit_pr_review(
        self,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Submit a review on a pull request.
        
        Args:
            pr_number: The pull request number
            body: The review body/summary
            event: One of "APPROVE", "REQUEST_CHANGES", "COMMENT"
            comments: Optional list of line-specific comments with:
                - path: File path
                - position: Line position in the diff (deprecated)
                - line: Line number in the diff
                - side: "LEFT" or "RIGHT" (for side-by-side diffs)
                - body: Comment text
                
        Returns:
            The created review object
        """
        payload = {
            "body": body,
            "event": event,
        }
        
        if comments:
            payload["comments"] = comments
            
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def add_pr_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
        side: str = "RIGHT",
    ) -> dict[str, Any]:
        """
        Add a review comment on a specific line of a PR.
        
        Args:
            pr_number: The pull request number
            body: Comment text
            commit_id: SHA of the commit to comment on
            path: Relative path of the file
            line: Line number in the file
            side: "LEFT" for old code, "RIGHT" for new code
        """
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": side,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_pr_review_comments(self, pr_number: int) -> list[dict[str, Any]]:
        """Get all review comments on a pull request."""
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments",
            params={"per_page": 100},
        )
        response.raise_for_status()
        
        comments = []
        for c in response.json():
            comments.append({
                "id": c.get("id"),
                "body": c.get("body"),
                "path": c.get("path"),
                "line": c.get("line"),
                "side": c.get("side"),
                "commit_id": c.get("commit_id"),
                "user": c.get("user", {}).get("login"),
                "created_at": c.get("created_at"),
            })
        return comments

    async def get_pr_reviews(self, pr_number: int) -> list[dict[str, Any]]:
        """
        Get all reviews on a pull request.
        
        Returns list of reviews with state like:
        - APPROVED
        - CHANGES_REQUESTED
        - COMMENTED
        - PENDING
        - DISMISSED
        """
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews",
            params={"per_page": 100},
        )
        response.raise_for_status()
        
        reviews = []
        for r in response.json():
            reviews.append({
                "id": r.get("id"),
                "user": r.get("user", {}).get("login"),
                "body": r.get("body"),
                "state": r.get("state"),
                "submitted_at": r.get("submitted_at"),
                "html_url": r.get("html_url"),
            })
        return reviews

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
    # GitHub Projects v2 Operations
    # =========================================================================

    async def list_projects(self, owner: str | None = None) -> list[GitHubProject]:
        """List all GitHub Projects v2 for the owner (user or organization)."""
        owner = owner or self.owner
        
        # Try organization first
        query = """
        query($login: String!) {
            organization(login: $login) {
                projectsV2(first: 20) {
                    nodes {
                        id
                        number
                        title
                        url
                    }
                }
            }
        }
        """
        try:
            data = await self._graphql(query, {"login": owner})
            if data.get("organization") and data["organization"].get("projectsV2"):
                return [
                    GitHubProject(
                        id=p["id"],
                        number=p["number"],
                        title=p["title"],
                        url=p["url"],
                    )
                    for p in data["organization"]["projectsV2"]["nodes"]
                ]
        except Exception:
            pass

        # Fall back to user
        query = """
        query($login: String!) {
            user(login: $login) {
                projectsV2(first: 20) {
                    nodes {
                        id
                        number
                        title
                        url
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"login": owner})
        if data.get("user") and data["user"].get("projectsV2"):
            return [
                GitHubProject(
                    id=p["id"],
                    number=p["number"],
                    title=p["title"],
                    url=p["url"],
                )
                for p in data["user"]["projectsV2"]["nodes"]
            ]
        return []

    async def get_project(self, project_number: int, owner: str | None = None) -> GitHubProject | None:
        """Get a specific GitHub Project v2 by number."""
        owner = owner or self.owner
        cache_key = f"{owner}/{project_number}"
        
        if cache_key in self._project_cache:
            return self._project_cache[cache_key]

        # Try organization first
        query = """
        query($login: String!, $number: Int!) {
            organization(login: $login) {
                projectV2(number: $number) {
                    id
                    number
                    title
                    url
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2Field {
                                id
                                name
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                options {
                                    id
                                    name
                                }
                            }
                            ... on ProjectV2IterationField {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = await self._graphql(query, {"login": owner, "number": project_number})
            if data.get("organization") and data["organization"].get("projectV2"):
                project = self._parse_project(data["organization"]["projectV2"])
                self._project_cache[cache_key] = project
                return project
        except Exception:
            pass

        # Fall back to user
        query = """
        query($login: String!, $number: Int!) {
            user(login: $login) {
                projectV2(number: $number) {
                    id
                    number
                    title
                    url
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2Field {
                                id
                                name
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                options {
                                    id
                                    name
                                }
                            }
                            ... on ProjectV2IterationField {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"login": owner, "number": project_number})
        if data.get("user") and data["user"].get("projectV2"):
            project = self._parse_project(data["user"]["projectV2"])
            self._project_cache[cache_key] = project
            return project
        return None

    async def create_project(self, title: str, owner: str | None = None) -> GitHubProject:
        """Create a new GitHub Project v2."""
        owner_id = await self._get_owner_node_id()
        
        mutation = """
        mutation($ownerId: ID!, $title: String!) {
            createProjectV2(input: {ownerId: $ownerId, title: $title}) {
                projectV2 {
                    id
                    number
                    title
                    url
                }
            }
        }
        """
        data = await self._graphql(mutation, {"ownerId": owner_id, "title": title})
        project_data = data["createProjectV2"]["projectV2"]
        
        return GitHubProject(
            id=project_data["id"],
            number=project_data["number"],
            title=project_data["title"],
            url=project_data["url"],
        )

    async def get_issue_node_id(self, issue_number: int) -> str:
        """Get the GraphQL node ID for an issue."""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                    id
                }
            }
        }
        """
        data = await self._graphql(query, {
            "owner": self.owner,
            "repo": self.repo,
            "number": issue_number,
        })
        return data["repository"]["issue"]["id"]

    async def add_issue_to_project(
        self,
        project_id: str,
        issue_number: int,
    ) -> GitHubProjectItem:
        """Add an issue to a GitHub Project v2."""
        issue_node_id = await self.get_issue_node_id(issue_number)
        
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
            addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item {
                    id
                }
            }
        }
        """
        data = await self._graphql(mutation, {
            "projectId": project_id,
            "contentId": issue_node_id,
        })
        
        return GitHubProjectItem(
            id=data["addProjectV2ItemById"]["item"]["id"],
            content_id=issue_node_id,
            content_type="Issue",
        )

    async def update_project_item_status(
        self,
        project_id: str,
        item_id: str,
        status_field_id: str,
        status_option_id: str,
    ) -> None:
        """Update the status field of a project item."""
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(
                input: {
                    projectId: $projectId
                    itemId: $itemId
                    fieldId: $fieldId
                    value: {singleSelectOptionId: $optionId}
                }
            ) {
                projectV2Item {
                    id
                }
            }
        }
        """
        await self._graphql(mutation, {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": status_field_id,
            "optionId": status_option_id,
        })

    async def get_or_create_project(self, title: str) -> GitHubProject:
        """Get a project by title, or create it if it doesn't exist."""
        projects = await self.list_projects()
        
        for project in projects:
            if project.title == title:
                # Fetch full project with fields
                full_project = await self.get_project(project.number)
                if full_project:
                    return full_project
        
        # Create new project
        new_project = await self.create_project(title)
        # Fetch the newly created project with fields
        return await self.get_project(new_project.number) or new_project

    async def sync_issue_to_project(
        self,
        project_number: int,
        issue_number: int,
        status: str | None = None,
    ) -> GitHubProjectItem:
        """
        Sync an issue to a GitHub Project and optionally set its status.
        
        Args:
            project_number: The project number (from URL)
            issue_number: The issue number to add
            status: Optional status name to set (e.g., "Todo", "In Progress", "Done")
        
        Returns:
            The project item
        """
        project = await self.get_project(project_number)
        if not project:
            raise ValueError(f"Project {project_number} not found")
        
        # Add issue to project
        item = await self.add_issue_to_project(project.id, issue_number)
        
        # Set status if provided and project has Status field
        if status and project.fields:
            status_field = next(
                (f for f in project.fields if f.name == "Status" and f.options),
                None
            )
            if status_field and status_field.options:
                status_option = next(
                    (o for o in status_field.options if o["name"].lower() == status.lower()),
                    None
                )
                if status_option:
                    await self.update_project_item_status(
                        project.id,
                        item.id,
                        status_field.id,
                        status_option["id"],
                    )
                    logger.debug(
                        "Set project item status",
                        issue_number=issue_number,
                        status=status,
                    )
        
        return item

    async def get_project_items_with_status(
        self,
        project_number: int,
    ) -> list[dict[str, Any]]:
        """
        Get all items from a GitHub Project v2 with their current status.
        
        Returns a list of dicts with:
        - issue_number: The GitHub issue number
        - issue_title: The issue title  
        - issue_state: open/closed
        - project_status: The status column name (e.g., "In Progress")
        - labels: List of label names
        
        This is used for "Pull from GitHub" sync to update local tasks.
        """
        project = await self.get_project(project_number)
        if not project:
            raise ValueError(f"Project {project_number} not found")
        
        # Find the Status field ID
        status_field_id = None
        if project.fields:
            status_field = next(
                (f for f in project.fields if f.name == "Status"),
                None
            )
            if status_field:
                status_field_id = status_field.id
        
        # Query project items with their content (issues) and status
        query = """
        query($login: String!, $number: Int!, $after: String) {
            user(login: $login) {
                projectV2(number: $number) {
                    items(first: 100, after: $after) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            id
                            fieldValueByName(name: "Status") {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                }
                            }
                            content {
                                ... on Issue {
                                    number
                                    title
                                    state
                                    labels(first: 20) {
                                        nodes {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        items = []
        after = None
        
        while True:
            data = await self._graphql(query, {
                "login": self.owner,
                "number": project_number,
                "after": after,
            })
            
            project_data = None
            if data.get("user") and data["user"].get("projectV2"):
                project_data = data["user"]["projectV2"]
            
            if not project_data:
                # Try organization
                org_query = query.replace("user(login:", "organization(login:")
                data = await self._graphql(org_query, {
                    "login": self.owner,
                    "number": project_number,
                    "after": after,
                })
                if data.get("organization") and data["organization"].get("projectV2"):
                    project_data = data["organization"]["projectV2"]
            
            if not project_data:
                break
            
            for node in project_data["items"]["nodes"]:
                content = node.get("content")
                if not content or not content.get("number"):
                    continue  # Skip draft items or non-issue content
                
                status_value = node.get("fieldValueByName")
                status_name = status_value.get("name") if status_value else None
                
                labels = []
                if content.get("labels") and content["labels"].get("nodes"):
                    labels = [l["name"] for l in content["labels"]["nodes"]]
                
                items.append({
                    "issue_number": content["number"],
                    "issue_title": content["title"],
                    "issue_state": content["state"].lower(),
                    "project_status": status_name,
                    "labels": labels,
                })
            
            # Handle pagination
            page_info = project_data["items"]["pageInfo"]
            if page_info["hasNextPage"]:
                after = page_info["endCursor"]
            else:
                break
        
        return items

    async def update_project_field_options(
        self,
        project_number: int,
        field_name: str = "Status",
        options: list[dict[str, str]] | None = None,
    ) -> GitHubProjectField:
        """
        Update the options for a single-select field in a GitHub Project v2.
        
        Uses the updateProjectV2Field mutation to set all options for a field.
        This allows programmatic configuration of project columns/statuses.
        
        Args:
            project_number: The project number
            field_name: The name of the field to update (default: "Status")
            options: List of option dicts with "name", "color", and "description"
                     If None, uses SDLC Agent default columns:
                     Backlog, To Do, In Progress, In Review, Done
        
        Returns:
            The updated field with new options
        
        Example:
            await github.update_project_field_options(
                project_number=2,
                options=[
                    {"name": "Backlog", "color": "GRAY", "description": "Not yet started"},
                    {"name": "To Do", "color": "BLUE", "description": "Ready to work on"},
                    {"name": "In Progress", "color": "YELLOW", "description": "Currently being worked on"},
                    {"name": "In Review", "color": "PURPLE", "description": "Awaiting review"},
                    {"name": "Done", "color": "GREEN", "description": "Completed"},
                ]
            )
        """
        # Default SDLC Agent columns if not specified
        if options is None:
            options = [
                {"name": "Backlog", "color": "GRAY", "description": "Not yet started"},
                {"name": "To Do", "color": "BLUE", "description": "Ready to work on"},
                {"name": "In Progress", "color": "YELLOW", "description": "Currently being worked on"},
                {"name": "In Review", "color": "PURPLE", "description": "Awaiting review"},
                {"name": "Done", "color": "GREEN", "description": "Completed"},
            ]
        
        # Get project with fields
        project = await self.get_project(project_number)
        if not project:
            raise ValueError(f"Project {project_number} not found")
        
        if not project.fields:
            raise ValueError(f"Project {project_number} has no fields")
        
        # Find the target field
        target_field = next(
            (f for f in project.fields if f.name == field_name and f.field_type == "single_select"),
            None
        )
        if not target_field:
            raise ValueError(f"Single-select field '{field_name}' not found in project {project_number}")
        
        # Build the mutation
        mutation = """
        mutation($fieldId: ID!, $singleSelectOptions: [ProjectV2SingleSelectFieldOptionInput!]!) {
            updateProjectV2Field(input: {
                fieldId: $fieldId,
                singleSelectOptions: $singleSelectOptions
            }) {
                projectV2Field {
                    ... on ProjectV2SingleSelectField {
                        id
                        name
                        options {
                            id
                            name
                            color
                            description
                        }
                    }
                }
            }
        }
        """
        
        # Format options for GraphQL - color must be uppercase enum value
        formatted_options = [
            {
                "name": opt["name"],
                "color": opt.get("color", "GRAY").upper(),
                "description": opt.get("description", ""),
            }
            for opt in options
        ]
        
        data = await self._graphql(mutation, {
            "fieldId": target_field.id,
            "singleSelectOptions": formatted_options,
        })
        
        # Clear cache to force refresh
        cache_key = f"{self.owner}/{project_number}"
        if cache_key in self._project_cache:
            del self._project_cache[cache_key]
        
        # Parse and return the updated field
        field_data = data["updateProjectV2Field"]["projectV2Field"]
        return GitHubProjectField(
            id=field_data["id"],
            name=field_data["name"],
            field_type="single_select",
            options=[{"id": o["id"], "name": o["name"]} for o in field_data["options"]],
        )

    def _parse_project(self, data: dict[str, Any]) -> GitHubProject:
        """Parse GraphQL response into GitHubProject."""
        fields = []
        if data.get("fields") and data["fields"].get("nodes"):
            for f in data["fields"]["nodes"]:
                if not f.get("id"):
                    continue
                field_type = "text"
                options = None
                if "options" in f:
                    field_type = "single_select"
                    options = f["options"]
                elif "configuration" in f:
                    field_type = "iteration"
                
                fields.append(GitHubProjectField(
                    id=f["id"],
                    name=f.get("name", ""),
                    field_type=field_type,
                    options=options,
                ))
        
        return GitHubProject(
            id=data["id"],
            number=data["number"],
            title=data["title"],
            url=data["url"],
            fields=fields if fields else None,
        )

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
