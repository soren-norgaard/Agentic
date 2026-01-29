# =============================================================================
# SDLC Agent - Code Review Agent
# =============================================================================
# Reviews code for quality, best practices, and security.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sdlc_agent.agents.base import (
    AgentPhase,
    AgentState,
    BaseAgent,
    MessageRole,
    ToolDefinition,
    ToolParameter,
)


@dataclass
class CodeReviewState(AgentState):
    """State specific to the code review agent."""

    # Review artifacts
    reviews: list[dict[str, Any]] = field(default_factory=list)
    issues_found: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    approval_status: str = "pending"


class CodeReviewAgent(BaseAgent[CodeReviewState]):
    """
    Code review agent.

    Responsibilities:
    - Review code for quality and best practices
    - Identify bugs, code smells, and anti-patterns
    - Check for security vulnerabilities
    - Suggest improvements
    - Approve or request changes
    """

    name = "code_review"
    description = "Reviews code for quality and best practices"
    phase = AgentPhase.CODE_REVIEW

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Code Review Agent with expertise in software quality.

Your responsibilities:
1. Review code for correctness, readability, and maintainability
2. Identify bugs, edge cases, and potential issues
3. Check for security vulnerabilities
4. Ensure code follows best practices and coding standards
5. Suggest improvements and optimizations
6. Verify adequate test coverage

When reviewing, consider:
- SOLID principles
- DRY (Don't Repeat Yourself)
- Code complexity and readability
- Error handling
- Performance implications
- Security best practices

Be constructive and specific. Reference line numbers when possible.
Prioritize issues by severity: critical, major, minor, suggestion."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="add_review_comment",
                description="Add a review comment on specific code",
                parameters=[
                    ToolParameter(
                        name="file_path",
                        description="Path to the file",
                    ),
                    ToolParameter(
                        name="line_number",
                        description="Line number (optional)",
                        required=False,
                    ),
                    ToolParameter(
                        name="severity",
                        description="Severity of the issue",
                        enum=["critical", "major", "minor", "suggestion"],
                    ),
                    ToolParameter(
                        name="category",
                        description="Category of the issue",
                        enum=["bug", "security", "performance", "style", "maintainability", "test"],
                    ),
                    ToolParameter(
                        name="comment",
                        description="The review comment",
                    ),
                    ToolParameter(
                        name="suggestion",
                        description="Suggested fix or improvement",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="approve_changes",
                description="Approve the code changes",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of the review",
                    ),
                ],
            ),
            ToolDefinition(
                name="request_changes",
                description="Request changes before approval",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of required changes",
                    ),
                    ToolParameter(
                        name="blocking_issues",
                        description="List of blocking issues (JSON array)",
                    ),
                ],
            ),
        ]

    async def process(self, state: CodeReviewState) -> CodeReviewState:
        """Process code review."""
        self.logger.info("Code review agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Get code from state (code_files set by developer) or metadata
        code_files = getattr(state, 'code_files', {}) or state.metadata.get("code_files", {})
        new_files = getattr(state, 'new_files', []) or state.metadata.get("new_files", [])
        
        code_to_review = ""
        if code_files:
            for path, content in code_files.items():
                code_to_review += f"\n--- {path} ---\n{content}\n"
        elif new_files:
            for f in new_files:
                code_to_review += f"\n--- {f.get('path', 'unknown')} ---\n{f.get('content', '')}\n"
        else:
            code_to_review = state.metadata.get("code_changes", "No code provided")
        
        state.add_message(
            MessageRole.USER,
            f"Please review the following code changes:\n\n{code_to_review}",
        )
        
        state = await self.run_with_tools(state)
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: CodeReviewState,
    ) -> tuple[str, CodeReviewState]:
        """Execute code review tools."""
        import json
        import uuid
        
        if tool_name == "add_review_comment":
            comment_id = str(uuid.uuid4())[:8]
            
            comment = {
                "id": comment_id,
                "file_path": tool_args.get("file_path"),
                "line_number": tool_args.get("line_number"),
                "severity": tool_args.get("severity"),
                "category": tool_args.get("category"),
                "comment": tool_args.get("comment"),
                "suggestion": tool_args.get("suggestion"),
            }
            
            state.issues_found.append(comment)
            
            severity = tool_args.get("severity", "minor")
            return f"Added {severity} comment on {tool_args.get('file_path')}: {tool_args.get('comment')[:50]}...", state
        
        elif tool_name == "approve_changes":
            state.approval_status = "approved"
            state.add_message(
                MessageRole.ASSISTANT,
                f"Code review approved.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Found {len(state.issues_found)} issues/suggestions.",
            )
            state.phase = AgentPhase.TESTING
            return f"Code approved with {len(state.issues_found)} comments", state
        
        elif tool_name == "request_changes":
            state.approval_status = "changes_requested"
            
            blocking = tool_args.get("blocking_issues", "[]")
            if isinstance(blocking, str):
                try:
                    blocking = json.loads(blocking)
                except json.JSONDecodeError:
                    blocking = []
            
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "code_review",
                "summary": tool_args.get("summary"),
                "blocking_issues": blocking,
            }
            
            return f"Changes requested: {len(blocking)} blocking issues", state
        
        return f"Unknown tool: {tool_name}", state
