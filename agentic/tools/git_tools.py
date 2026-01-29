"""Git tools for agents."""

import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel


class GitOperationResult(BaseModel):
    """Result of a git operation."""
    success: bool
    message: str
    data: Any = None


def run_git_command(args: list[str], cwd: str | None = None) -> tuple[bool, str, str]:
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


@tool
def git_init(repo_path: str) -> GitOperationResult:
    """
    Initialize a new git repository.
    
    Args:
        repo_path: Path where the repository should be initialized
        
    Returns:
        GitOperationResult with success status
    """
    path = Path(repo_path)
    path.mkdir(parents=True, exist_ok=True)
    
    success, stdout, stderr = run_git_command(["init"], cwd=str(path))
    
    if success:
        return GitOperationResult(
            success=True,
            message=f"Git repository initialized at {repo_path}",
            data={"path": repo_path},
        )
    return GitOperationResult(
        success=False,
        message=f"Failed to initialize git repository: {stderr}",
    )


@tool
def git_commit(repo_path: str, message: str, add_all: bool = True) -> GitOperationResult:
    """
    Commit changes to the repository.
    
    Args:
        repo_path: Path to the repository
        message: Commit message
        add_all: Whether to add all changes before committing
        
    Returns:
        GitOperationResult with commit info
    """
    if add_all:
        success, _, stderr = run_git_command(["add", "."], cwd=repo_path)
        if not success:
            return GitOperationResult(
                success=False,
                message=f"Failed to stage changes: {stderr}",
            )
    
    success, stdout, stderr = run_git_command(
        ["commit", "-m", message],
        cwd=repo_path,
    )
    
    if success:
        return GitOperationResult(
            success=True,
            message=f"Changes committed: {message}",
            data={"output": stdout},
        )
    
    # Check if there's nothing to commit
    if "nothing to commit" in stderr or "nothing to commit" in stdout:
        return GitOperationResult(
            success=True,
            message="Nothing to commit",
        )
    
    return GitOperationResult(
        success=False,
        message=f"Failed to commit: {stderr}",
    )


@tool
def git_status(repo_path: str) -> GitOperationResult:
    """
    Get the status of the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        GitOperationResult with status info
    """
    success, stdout, stderr = run_git_command(["status", "--short"], cwd=repo_path)
    
    if success:
        lines = stdout.strip().split("\n") if stdout.strip() else []
        return GitOperationResult(
            success=True,
            message=f"Repository has {len(lines)} changed files",
            data={"changes": lines, "raw": stdout},
        )
    return GitOperationResult(
        success=False,
        message=f"Failed to get status: {stderr}",
    )


@tool
def git_diff(repo_path: str, staged: bool = False) -> GitOperationResult:
    """
    Get the diff of changes.
    
    Args:
        repo_path: Path to the repository
        staged: Whether to show staged changes only
        
    Returns:
        GitOperationResult with diff
    """
    args = ["diff"]
    if staged:
        args.append("--staged")
    
    success, stdout, stderr = run_git_command(args, cwd=repo_path)
    
    if success:
        return GitOperationResult(
            success=True,
            message="Diff retrieved",
            data={"diff": stdout},
        )
    return GitOperationResult(
        success=False,
        message=f"Failed to get diff: {stderr}",
    )


@tool
def git_log(repo_path: str, count: int = 10) -> GitOperationResult:
    """
    Get the commit log.
    
    Args:
        repo_path: Path to the repository
        count: Number of commits to retrieve
        
    Returns:
        GitOperationResult with commit log
    """
    success, stdout, stderr = run_git_command(
        ["log", f"-{count}", "--oneline"],
        cwd=repo_path,
    )
    
    if success:
        commits = stdout.strip().split("\n") if stdout.strip() else []
        return GitOperationResult(
            success=True,
            message=f"Retrieved {len(commits)} commits",
            data={"commits": commits},
        )
    return GitOperationResult(
        success=False,
        message=f"Failed to get log: {stderr}",
    )


@tool
def git_branch(repo_path: str, branch_name: str | None = None) -> GitOperationResult:
    """
    List branches or create a new branch.
    
    Args:
        repo_path: Path to the repository
        branch_name: Name of branch to create (if None, lists branches)
        
    Returns:
        GitOperationResult with branch info
    """
    if branch_name:
        success, stdout, stderr = run_git_command(
            ["checkout", "-b", branch_name],
            cwd=repo_path,
        )
        if success:
            return GitOperationResult(
                success=True,
                message=f"Created and switched to branch: {branch_name}",
            )
        return GitOperationResult(
            success=False,
            message=f"Failed to create branch: {stderr}",
        )
    else:
        success, stdout, stderr = run_git_command(["branch"], cwd=repo_path)
        if success:
            branches = [b.strip() for b in stdout.strip().split("\n") if b.strip()]
            return GitOperationResult(
                success=True,
                message=f"Found {len(branches)} branches",
                data={"branches": branches},
            )
        return GitOperationResult(
            success=False,
            message=f"Failed to list branches: {stderr}",
        )
