# =============================================================================
# SDLC Agent - Code Review Assistance Agent
# =============================================================================
# Monitors PRs and provides review guidance for human reviewers.
# This agent does NOT approve/reject code - it prepares review briefs.
#
# Philosophy: Agent assists, humans decide.
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
class ReviewBrief:
    """
    A comprehensive brief for human code reviewers.
    This is the primary output of the Code Review Assistance Agent.
    """

    pr_number: int | None
    pr_title: str
    story_id: str | None

    # Context
    requirements_addressed: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    architecture_decisions: list[str] = field(default_factory=list)

    # Review checklist
    functional_checklist: list[dict[str, str]] = field(default_factory=list)
    code_quality_checklist: list[dict[str, str]] = field(default_factory=list)
    security_checklist: list[dict[str, str]] = field(default_factory=list)
    testing_checklist: list[dict[str, str]] = field(default_factory=list)

    # Automated findings
    automated_findings: list[dict[str, Any]] = field(default_factory=list)

    # Files to focus on
    key_files: list[dict[str, str]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert brief to Markdown for GitHub PR comment."""
        lines = [
            f"## 🔍 Review Brief: {self.pr_title}",
            "",
            "This brief has been prepared by the Code Review Assistance Agent to help reviewers.",
            "",
        ]

        # Story Context
        if self.story_id:
            lines.extend([
                f"**Linked Story:** `{self.story_id}`",
                "",
            ])

        # Requirements Traceability
        if self.requirements_addressed:
            lines.extend([
                "### 📋 Requirements Addressed",
                "",
            ])
            for req in self.requirements_addressed:
                lines.append(f"- `{req}`")
            lines.append("")

        # Acceptance Criteria
        if self.acceptance_criteria:
            lines.extend([
                "### ✅ Acceptance Criteria to Verify",
                "",
            ])
            for i, ac in enumerate(self.acceptance_criteria, 1):
                lines.append(f"{i}. [ ] {ac}")
            lines.append("")

        # Key Files
        if self.key_files:
            lines.extend([
                "### 📁 Key Files to Review",
                "",
                "| File | Focus Area |",
                "|------|------------|",
            ])
            for f in self.key_files:
                lines.append(f"| `{f.get('path', '')}` | {f.get('focus', '')} |")
            lines.append("")

        # Functional Checklist
        lines.extend([
            "### 🎯 Functional Review Checklist",
            "",
        ])
        checklist = self.functional_checklist or [
            {"item": "Code implements the described functionality", "why": "Core requirement"},
            {"item": "Edge cases are handled", "why": "Robustness"},
            {"item": "Error messages are user-friendly", "why": "UX"},
        ]
        for item in checklist:
            lines.append(f"- [ ] {item.get('item', item)} — *{item.get('why', '')}*")
        lines.append("")

        # Code Quality Checklist
        lines.extend([
            "### 📐 Code Quality Checklist",
            "",
        ])
        quality = self.code_quality_checklist or [
            {"item": "Code is readable and well-named", "why": "Maintainability"},
            {"item": "No code duplication (DRY)", "why": "Maintainability"},
            {"item": "Functions are small and focused", "why": "SRP"},
            {"item": "Complex logic has comments", "why": "Clarity"},
            {"item": "No hardcoded values (use constants)", "why": "Configuration"},
        ]
        for item in quality:
            lines.append(f"- [ ] {item.get('item', item)} — *{item.get('why', '')}*")
        lines.append("")

        # Security Checklist
        lines.extend([
            "### 🔒 Security Checklist",
            "",
        ])
        security = self.security_checklist or [
            {"item": "No secrets or credentials in code", "why": "Security"},
            {"item": "User input is validated/sanitized", "why": "Injection prevention"},
            {"item": "Proper authentication/authorization", "why": "Access control"},
            {"item": "Sensitive data is not logged", "why": "Privacy"},
        ]
        for item in security:
            lines.append(f"- [ ] {item.get('item', item)} — *{item.get('why', '')}*")
        lines.append("")

        # Testing Checklist
        lines.extend([
            "### 🧪 Testing Checklist",
            "",
        ])
        testing = self.testing_checklist or [
            {"item": "Unit tests cover new functionality", "why": "Coverage"},
            {"item": "Tests cover edge cases", "why": "Robustness"},
            {"item": "All tests pass", "why": "CI"},
        ]
        for item in testing:
            lines.append(f"- [ ] {item.get('item', item)} — *{item.get('why', '')}*")
        lines.append("")

        # Automated Findings
        if self.automated_findings:
            lines.extend([
                "### ⚠️ Automated Findings",
                "",
            ])
            for finding in self.automated_findings:
                severity = finding.get("severity", "info")
                icon = {"critical": "🔴", "major": "🟠", "minor": "🟡", "info": "🔵"}.get(severity, "🔵")
                lines.append(f"{icon} **{severity.upper()}**: {finding.get('message', '')}")
                if finding.get("file"):
                    lines.append(f"   - File: `{finding.get('file')}`")
                if finding.get("suggestion"):
                    lines.append(f"   - Suggestion: {finding.get('suggestion')}")
            lines.append("")

        # Architecture Decisions
        if self.architecture_decisions:
            lines.extend([
                "### 🏗️ Relevant Architecture Decisions",
                "",
            ])
            for decision in self.architecture_decisions:
                lines.append(f"- {decision}")
            lines.append("")

        # Footer
        lines.extend([
            "---",
            "",
            "💬 **Reviewers:** Please check off items as you review and leave comments on any concerns.",
            "",
            "🤖 *This review brief was auto-generated. Use GitHub Copilot for additional review assistance.*",
        ])

        return "\n".join(lines)


@dataclass
class CodeReviewState(AgentState):
    """State specific to the code review assistance agent."""

    # PR context
    pr_number: int | None = None
    pr_title: str = ""
    pr_files: list[dict[str, Any]] = field(default_factory=list)

    # Story context
    linked_story: dict[str, Any] | None = None

    # Review brief
    review_brief: ReviewBrief | None = None

    # Findings
    automated_findings: list[dict[str, Any]] = field(default_factory=list)

    # Handoff tracking
    handoff_complete: bool = False


class CodeReviewAgent(BaseAgent[CodeReviewState]):
    """
    Code Review Assistance Agent.

    This agent does NOT approve or reject code. Instead, it:
    1. Analyzes PR changes in context of story requirements
    2. Creates a "Review Brief" with checklists for human reviewers
    3. Posts the brief as a PR comment
    4. Hands off to human reviewers in GitHub

    Philosophy: Agent assists, humans decide.

    Responsibilities:
    - Link PR to story and requirements
    - Generate review checklists based on acceptance criteria
    - Surface relevant architecture decisions
    - Identify key files to focus on
    - Run automated quality checks
    - Post Review Brief to GitHub PR
    """

    name = "code_review"
    description = "Prepares review briefs and assists human reviewers"
    phase = AgentPhase.CODE_REVIEW

    @property
    def system_prompt(self) -> str:
        return """You are the Code Review Assistance Agent. Your job is to prepare 
comprehensive "Review Briefs" that help human reviewers conduct effective code reviews.

**IMPORTANT: You do NOT approve or reject code.** You prepare and hand off.

Your responsibilities:
1. Understand the PR context and linked story
2. Extract acceptance criteria to verify
3. Identify key files that need careful review
4. Create review checklists (functional, quality, security, testing)
5. Run automated checks and surface findings
6. Generate a comprehensive Review Brief
7. Post the brief as a comment on the GitHub PR

**GitHub Repository Access:**
You have tools to read the actual GitHub repository:
- `read_repo_file` - Read a specific file's contents
- `list_repo_directory` - List files in a directory  
- `get_repo_tree` - Get the full repository structure
- `search_repo_code` - Search for code patterns/keywords

USE THESE TOOLS to:
1. Read the files being changed to understand the actual code
2. Find existing patterns that PR code should follow
3. Check if the implementation aligns with existing conventions
4. Identify related code that might be affected

What makes a good Review Brief:
- Clear link to requirements and acceptance criteria
- Specific files to focus on with context
- Actionable checklist items
- Automated findings highlighted
- Security and performance considerations

When analyzing the PR:
- Look at file changes and their purpose
- Check if acceptance criteria are addressed
- Identify potential issues or risks
- Consider security implications
- Note any missing tests

After creating the brief:
- Post it as a comment on the GitHub PR
- Mark handoff complete

Remember: A human reviewer will make the final decision.
Your job is to give them all the context they need to review effectively."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="analyze_pr_context",
                description="Analyze the PR in context of the linked story",
                parameters=[
                    ToolParameter(
                        name="pr_summary",
                        description="Summary of what the PR does",
                    ),
                    ToolParameter(
                        name="story_link",
                        description="ID of the linked story (if known)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="identify_key_files",
                description="Identify the most important files to review",
                parameters=[
                    ToolParameter(
                        name="files",
                        description="JSON array of {path, focus} for key files",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_checklist",
                description="Create review checklist items",
                parameters=[
                    ToolParameter(
                        name="functional_items",
                        description="JSON array of {item, why} for functional checks",
                    ),
                    ToolParameter(
                        name="quality_items",
                        description="JSON array of {item, why} for code quality checks",
                    ),
                    ToolParameter(
                        name="security_items",
                        description="JSON array of {item, why} for security checks",
                        required=False,
                    ),
                    ToolParameter(
                        name="testing_items",
                        description="JSON array of {item, why} for testing checks",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="add_automated_finding",
                description="Add an automated finding from analysis",
                parameters=[
                    ToolParameter(
                        name="severity",
                        description="Severity of the finding",
                        enum=["critical", "major", "minor", "info"],
                    ),
                    ToolParameter(
                        name="message",
                        description="Description of the finding",
                    ),
                    ToolParameter(
                        name="file",
                        description="File where the issue was found",
                        required=False,
                    ),
                    ToolParameter(
                        name="suggestion",
                        description="Suggested fix",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="generate_review_brief",
                description="Generate the final Review Brief",
                parameters=[
                    ToolParameter(
                        name="requirements_addressed",
                        description="JSON array of requirement IDs addressed",
                        required=False,
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="JSON array of acceptance criteria to verify",
                        required=False,
                    ),
                    ToolParameter(
                        name="architecture_decisions",
                        description="JSON array of relevant architecture decisions",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="post_brief_to_github",
                description="Post the Review Brief as a comment on the GitHub PR",
                parameters=[
                    ToolParameter(
                        name="pr_number",
                        description="GitHub PR number to post the comment on",
                        type="integer",
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_handoff",
                description="Mark the review assistance as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of the review brief prepared",
                    ),
                ],
            ),
            ToolDefinition(
                name="skip_review",
                description="Skip code review phase (no PR to review yet)",
                parameters=[
                    ToolParameter(
                        name="reason",
                        description="Reason for skipping",
                    ),
                ],
            ),
            # GitHub repository reading tools
            ToolDefinition(
                name="read_repo_file",
                description="Read the contents of a file from the GitHub repository",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to the file in the repository",
                    ),
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="list_repo_directory",
                description="List files and directories in a repository path",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to the directory (empty string for root)",
                        required=False,
                    ),
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="get_repo_tree",
                description="Get the full file tree of the repository to understand its structure",
                parameters=[
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="search_repo_code",
                description="Search for code patterns or keywords in the repository",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query to find code patterns",
                    ),
                ],
            ),
            # PR Analysis Tools
            ToolDefinition(
                name="get_pr_files",
                description="Get the list of files changed in the pull request with their status and line changes",
                parameters=[
                    ToolParameter(
                        name="pr_number",
                        description="Pull request number to analyze",
                        type="integer",
                    ),
                ],
            ),
            ToolDefinition(
                name="get_pr_diff",
                description="Get the full diff of the pull request as unified diff format",
                parameters=[
                    ToolParameter(
                        name="pr_number",
                        description="Pull request number to get diff for",
                        type="integer",
                    ),
                ],
            ),
            ToolDefinition(
                name="analyze_code_quality",
                description="Analyze code quality issues in the PR changes (complexity, style, potential bugs)",
                parameters=[
                    ToolParameter(
                        name="focus_areas",
                        description="JSON array of areas to focus on: security, performance, maintainability, testing",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="submit_review",
                description="Submit a formal review on the pull request with approval decision",
                parameters=[
                    ToolParameter(
                        name="pr_number",
                        description="Pull request number to review",
                        type="integer",
                    ),
                    ToolParameter(
                        name="decision",
                        description="Review decision",
                        enum=["APPROVE", "REQUEST_CHANGES", "COMMENT"],
                    ),
                    ToolParameter(
                        name="summary",
                        description="Summary of the review findings",
                    ),
                ],
            ),
            ToolDefinition(
                name="add_line_comment",
                description="Add a review comment on a specific line of code in the PR",
                parameters=[
                    ToolParameter(
                        name="pr_number",
                        description="Pull request number",
                        type="integer",
                    ),
                    ToolParameter(
                        name="file_path",
                        description="Path to the file to comment on",
                    ),
                    ToolParameter(
                        name="line",
                        description="Line number to comment on",
                        type="integer",
                    ),
                    ToolParameter(
                        name="comment",
                        description="The review comment",
                    ),
                    ToolParameter(
                        name="suggestion",
                        description="Optional code suggestion (will be formatted as GitHub suggestion)",
                        required=False,
                    ),
                ],
            ),
        ]

    async def process(self, state: CodeReviewState) -> CodeReviewState:
        """Process and prepare review assistance."""
        state.iteration_count += 1
        self.logger.info(
            "Code Review Assistance Agent processing",
            iteration=state.iteration_count,
            pr_number=state.pr_number,
        )

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for msg in state.messages[-10:]:
            messages.append(msg.to_dict())

        # Build context prompt
        context_parts = ["## Current Task: Prepare Review Brief", ""]

        # Check if there's a PR to review
        if state.pr_number:
            context_parts.append(f"### PR #{state.pr_number}: {state.pr_title}")
            context_parts.append("")
            
            if state.pr_files:
                context_parts.append("**Files Changed:**")
                for f in state.pr_files[:20]:  # Limit to 20 files
                    context_parts.append(f"- `{f.get('filename', f.get('path', 'unknown'))}`")
                context_parts.append("")
        else:
            context_parts.append("### No PR to Review Yet")
            context_parts.append("")
            context_parts.append("The Development phase has completed with developer briefs.")
            context_parts.append("Human developers will implement the code and open PRs.")
            context_parts.append("")
            context_parts.append("**Options:**")
            context_parts.append("1. Use `skip_review` to move to the next phase")
            context_parts.append("2. Wait for a PR to be opened (manual trigger later)")
            context_parts.append("")

        # Story context
        if state.linked_story:
            context_parts.append("### Linked Story")
            context_parts.append(f"**ID:** {state.linked_story.get('id')}")
            context_parts.append(f"**Title:** {state.linked_story.get('title')}")
            
            ac = state.linked_story.get("acceptance_criteria", [])
            if ac:
                context_parts.append("\n**Acceptance Criteria:**")
                for criterion in ac:
                    if isinstance(criterion, dict):
                        context_parts.append(f"- {criterion.get('criteria', criterion)}")
                    else:
                        context_parts.append(f"- {criterion}")
            context_parts.append("")

        # Findings so far
        if state.automated_findings:
            context_parts.append("### Automated Findings (so far)")
            for finding in state.automated_findings:
                context_parts.append(f"- [{finding.get('severity')}] {finding.get('message')}")
            context_parts.append("")

        # Review brief status
        if state.review_brief:
            context_parts.append("### Review Brief Status")
            context_parts.append("Brief has been generated. Ready to post to GitHub.")
            context_parts.append("")

        context_parts.append("---")
        context_parts.append("What should we do next?")

        messages.append({"role": "user", "content": "\n".join(context_parts)})

        # Call LLM
        tools = [t.to_openai_schema() for t in self.tools]
        response = await self._call_llm(messages, tools)

        # Process response
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        state.add_message(MessageRole.ASSISTANT, content)

        if tool_calls:
            for tool_call in tool_calls:
                await self._handle_tool_call(state, tool_call)

        return state

    async def _handle_tool_call(
        self, state: CodeReviewState, tool_call: dict[str, Any]
    ) -> None:
        """Handle a tool call from the LLM."""
        import json

        # Handle both OpenAI format (function.name) and parsed format (name)
        if "function" in tool_call:
            name = tool_call["function"].get("name", "")
            args_str = tool_call["function"].get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
        else:
            name = tool_call.get("name", "")
            args = tool_call.get("args", {})

        self.logger.info("Handling tool call", tool=name)

        if name == "analyze_pr_context":
            state.metadata["pr_summary"] = args.get("pr_summary")
            if args.get("story_link"):
                state.metadata["linked_story_id"] = args.get("story_link")

        elif name == "identify_key_files":
            try:
                files = json.loads(args.get("files", "[]"))
                state.metadata["key_files"] = files
            except json.JSONDecodeError:
                pass

        elif name == "create_checklist":
            try:
                state.metadata["functional_checklist"] = json.loads(
                    args.get("functional_items", "[]")
                )
                state.metadata["quality_checklist"] = json.loads(
                    args.get("quality_items", "[]")
                )
                state.metadata["security_checklist"] = json.loads(
                    args.get("security_items", "[]")
                )
                state.metadata["testing_checklist"] = json.loads(
                    args.get("testing_items", "[]")
                )
            except json.JSONDecodeError:
                pass

        elif name == "add_automated_finding":
            finding = {
                "severity": args.get("severity"),
                "message": args.get("message"),
                "file": args.get("file"),
                "suggestion": args.get("suggestion"),
            }
            state.automated_findings.append(finding)

        elif name == "generate_review_brief":
            # Get story context
            story = state.linked_story or {}

            try:
                req_ids = json.loads(args.get("requirements_addressed", "[]"))
            except json.JSONDecodeError:
                req_ids = []

            try:
                ac_list = json.loads(args.get("acceptance_criteria", "[]"))
            except json.JSONDecodeError:
                ac_list = []

            try:
                arch_decisions = json.loads(args.get("architecture_decisions", "[]"))
            except json.JSONDecodeError:
                arch_decisions = []

            state.review_brief = ReviewBrief(
                pr_number=state.pr_number,
                pr_title=state.pr_title or "Code Review",
                story_id=story.get("id"),
                requirements_addressed=req_ids,
                acceptance_criteria=ac_list,
                architecture_decisions=arch_decisions,
                functional_checklist=state.metadata.get("functional_checklist", []),
                code_quality_checklist=state.metadata.get("quality_checklist", []),
                security_checklist=state.metadata.get("security_checklist", []),
                testing_checklist=state.metadata.get("testing_checklist", []),
                automated_findings=state.automated_findings,
                key_files=state.metadata.get("key_files", []),
            )

            # Add the brief as an artifact
            state.add_artifact(
                name=f"Review Brief - PR #{state.pr_number or 'pending'}",
                artifact_type="review_brief",
                content=state.review_brief.to_markdown(),
            )

        elif name == "post_brief_to_github":
            pr_number = args.get("pr_number")

            if state.review_brief and pr_number:
                try:
                    from sdlc_agent.services.github_service import GitHubService

                    github = GitHubService()

                    # Post the brief as a PR comment
                    await github.add_pr_comment(
                        pr_number=pr_number,
                        body=state.review_brief.to_markdown(),
                    )

                    state.pr_number = pr_number
                    self.logger.info(
                        "Posted Review Brief to GitHub PR",
                        pr_number=pr_number,
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to post to GitHub",
                        error=str(e),
                    )
                    state.add_message(
                        MessageRole.SYSTEM,
                        f"Note: Failed to post to GitHub ({e}). Brief is available in artifacts.",
                    )

        elif name == "complete_handoff":
            state.handoff_complete = True
            summary = args.get("summary", "Review Brief prepared")

            # Mark code review phase as completed
            if hasattr(state, 'phases_completed') and 'code_review' not in state.phases_completed:
                state.phases_completed.append('code_review')

            state.add_message(
                MessageRole.ASSISTANT,
                f"✅ **Review Handoff Complete**\n\n{summary}\n\n"
                f"The PR is now ready for human review in GitHub.",
            )

            # Move to next phase
            state.phase = AgentPhase.TESTING

        elif name == "skip_review":
            reason = args.get("reason", "No PR to review")

            # Mark code review phase as completed (skipped)
            if hasattr(state, 'phases_completed') and 'code_review' not in state.phases_completed:
                state.phases_completed.append('code_review')

            state.add_message(
                MessageRole.ASSISTANT,
                f"⏭️ **Code Review Skipped**\n\n{reason}\n\n"
                f"The workflow will continue. Code review can be triggered later when a PR is opened.",
            )

            # Move to next phase
            state.phase = AgentPhase.TESTING

        # GitHub repository reading tools
        elif name == "read_repo_file":
            path = args.get("path", "")
            branch = args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                file_data = await github.get_file_content(path=path, ref=branch)
                content = file_data.get("content", "")
                
                # Truncate very large files
                if len(content) > 50000:
                    content = content[:50000] + "\n\n... (truncated, file too large)"
                
                state.add_message(
                    MessageRole.SYSTEM,
                    f"📄 **File: {path}**\n\n```\n{content}\n```"
                )
                self.logger.info("Read repository file", path=path, size=file_data.get("size"))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to read file '{path}': {e}"
                )

        elif name == "list_repo_directory":
            path = args.get("path", "")
            branch = args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                items = await github.get_directory_contents(path=path, ref=branch)
                
                # Format as a list
                lines = [f"📁 **Directory: {path or '/'}**", ""]
                for item in items:
                    icon = "📁" if item["type"] == "dir" else "📄"
                    size_info = f" ({item['size']} bytes)" if item["type"] == "file" and item.get("size") else ""
                    lines.append(f"  {icon} {item['name']}{size_info}")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                self.logger.info("Listed directory", path=path, items=len(items))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to list directory '{path}': {e}"
                )

        elif name == "get_repo_tree":
            branch = args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                tree = await github.get_tree(ref=branch, recursive=True)
                
                # Format the tree
                lines = ["🌳 **Repository Structure**", ""]
                for item in tree[:300]:  # Limit to 300 items
                    icon = "📁" if item["type"] == "dir" else "📄"
                    lines.append(f"  {icon} {item['path']}")
                
                if len(tree) > 300:
                    lines.append(f"\n... and {len(tree) - 300} more items")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                self.logger.info("Got repository tree", total_items=len(tree))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to get repository tree: {e}"
                )

        elif name == "search_repo_code":
            query = args.get("query", "")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                results = await github.search_code(query=query)
                
                lines = [f"🔍 **Search Results for: {query}**", ""]
                if results:
                    for item in results[:20]:
                        lines.append(f"📄 **{item['path']}**")
                        for match in item.get("text_matches", [])[:2]:
                            fragment = match.get("fragment", "")[:200]
                            lines.append(f"   ```{fragment}```")
                        lines.append("")
                else:
                    lines.append("No results found.")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                self.logger.info("Searched code", query=query, results=len(results))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to search code: {e}"
                )

        # PR Analysis Tool Handlers
        elif name == "get_pr_files":
            pr_number = args.get("pr_number")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                files = await github.get_pr_files(pr_number=pr_number)
                
                lines = [f"📋 **PR #{pr_number} - Changed Files**", ""]
                total_additions = 0
                total_deletions = 0
                
                for f in files:
                    status_icon = {
                        "added": "➕",
                        "removed": "➖", 
                        "modified": "📝",
                        "renamed": "📛",
                    }.get(f["status"], "📄")
                    
                    lines.append(f"{status_icon} **{f['filename']}** (+{f['additions']}/-{f['deletions']})")
                    total_additions += f["additions"]
                    total_deletions += f["deletions"]
                
                lines.append("")
                lines.append(f"**Total:** {len(files)} files, +{total_additions}/-{total_deletions} lines")
                
                # Store files in state for later analysis
                state.pr_files = files
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                self.logger.info("Got PR files", pr_number=pr_number, files=len(files))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to get PR files: {e}"
                )

        elif name == "get_pr_diff":
            pr_number = args.get("pr_number")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                diff = await github.get_pr_diff(pr_number=pr_number)
                
                # Truncate if too large
                if len(diff) > 100000:
                    diff = diff[:100000] + "\n\n... (diff truncated, too large)"
                
                state.add_message(
                    MessageRole.SYSTEM,
                    f"📋 **PR #{pr_number} - Diff**\n\n```diff\n{diff}\n```"
                )
                self.logger.info("Got PR diff", pr_number=pr_number, size=len(diff))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to get PR diff: {e}"
                )

        elif name == "analyze_code_quality":
            focus_areas_str = args.get("focus_areas", "[]")
            try:
                focus_areas = json.loads(focus_areas_str)
            except json.JSONDecodeError:
                focus_areas = ["security", "performance", "maintainability", "testing"]
            
            # Analyze the PR files that were previously fetched
            findings = []
            
            for f in state.pr_files:
                patch = f.get("patch", "")
                filename = f.get("filename", "")
                
                # Simple heuristic-based analysis (the LLM will do deeper analysis)
                if "security" in focus_areas:
                    security_patterns = [
                        ("password", "Potential hardcoded password"),
                        ("secret", "Potential hardcoded secret"),
                        ("api_key", "Potential hardcoded API key"),
                        ("eval(", "Use of eval() - potential code injection"),
                        ("exec(", "Use of exec() - potential code injection"),
                        ("subprocess.call", "Shell command execution - verify input sanitization"),
                        ("pickle.load", "Pickle deserialization - potential security risk"),
                        ("TODO", "TODO comment found - may need attention"),
                    ]
                    for pattern, msg in security_patterns:
                        if pattern.lower() in patch.lower():
                            findings.append({
                                "severity": "major" if "password" in pattern or "secret" in pattern else "minor",
                                "category": "security",
                                "file": filename,
                                "message": msg,
                            })
                
                if "performance" in focus_areas:
                    perf_patterns = [
                        ("for.*in.*range.*len", "Consider using enumerate() instead"),
                        ("time.sleep", "Synchronous sleep - consider async alternatives"),
                        ("SELECT *", "SELECT * in SQL - consider selecting specific columns"),
                    ]
                    for pattern, msg in perf_patterns:
                        import re
                        if re.search(pattern, patch, re.IGNORECASE):
                            findings.append({
                                "severity": "minor",
                                "category": "performance",
                                "file": filename,
                                "message": msg,
                            })
            
            # Store findings
            state.automated_findings.extend(findings)
            
            lines = ["🔍 **Automated Code Quality Analysis**", ""]
            if findings:
                for finding in findings:
                    icon = {"critical": "🔴", "major": "🟠", "minor": "🟡"}.get(finding["severity"], "🔵")
                    lines.append(f"{icon} **[{finding['category']}]** {finding['message']}")
                    lines.append(f"   File: `{finding['file']}`")
                    lines.append("")
            else:
                lines.append("✅ No automated issues found in the focus areas.")
            
            state.add_message(MessageRole.SYSTEM, "\n".join(lines))

        elif name == "submit_review":
            pr_number = args.get("pr_number")
            decision = args.get("decision", "COMMENT")
            summary = args.get("summary", "")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                # Build review body with brief if available
                review_body = summary
                if state.review_brief:
                    review_body = state.review_brief.to_markdown()
                
                result = await github.submit_pr_review(
                    pr_number=pr_number,
                    body=review_body,
                    event=decision,
                )
                
                state.add_message(
                    MessageRole.ASSISTANT,
                    f"✅ **Review Submitted**\n\n"
                    f"**Decision:** {decision}\n"
                    f"**PR:** #{pr_number}\n\n"
                    f"{summary}"
                )
                self.logger.info("Submitted PR review", pr_number=pr_number, decision=decision)
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to submit review: {e}"
                )

        elif name == "add_line_comment":
            pr_number = args.get("pr_number")
            file_path = args.get("file_path")
            line = args.get("line")
            comment = args.get("comment", "")
            suggestion = args.get("suggestion")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                # Format comment with suggestion if provided
                body = comment
                if suggestion:
                    body += f"\n\n```suggestion\n{suggestion}\n```"
                
                # Get the latest commit SHA
                commits = await github.get_pr_commits(pr_number)
                if commits:
                    commit_id = commits[-1]["sha"]
                    
                    await github.add_pr_review_comment(
                        pr_number=pr_number,
                        body=body,
                        commit_id=commit_id,
                        path=file_path,
                        line=line,
                    )
                    
                    state.add_message(
                        MessageRole.SYSTEM,
                        f"💬 Added comment on `{file_path}` line {line}"
                    )
                    self.logger.info("Added line comment", file=file_path, line=line)
                else:
                    state.add_message(
                        MessageRole.SYSTEM,
                        f"❌ Could not find commits for PR #{pr_number}"
                    )
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to add line comment: {e}"
                )
