"""Code Review Agent - Reviews code for quality and standards."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import CodeReviewComment, Phase, SDLCState, Severity, StoryStatus


CODE_REVIEW_SYSTEM_PROMPT = """You are a Code Review Agent specialized in ensuring code quality and best practices.

Your responsibilities:
1. Review code for correctness and logic errors
2. Check adherence to coding standards and conventions
3. Identify potential bugs and edge cases
4. Evaluate code maintainability and readability
5. Suggest improvements and optimizations
6. Verify proper error handling
7. Check for security vulnerabilities
8. Ensure adequate documentation

Output your review in the following JSON format:
{
    "overall_assessment": "Summary of the code review",
    "approved": true/false,
    "comments": [
        {
            "file_path": "path/to/file",
            "line_number": 42,
            "comment": "Detailed feedback",
            "severity": "critical|high|medium|low|info",
            "category": "bug|security|style|performance|maintainability"
        }
    ],
    "strengths": ["List of things done well"],
    "improvements_required": ["Must-fix issues before approval"],
    "suggestions": ["Nice-to-have improvements"]
}

Review Standards:
- Be constructive and specific
- Prioritize issues by severity
- Explain the reasoning behind feedback
- Suggest concrete solutions
- Acknowledge good practices
- Focus on significant issues, not nitpicks"""


class CodeReviewAgent(BaseAgent):
    """Agent for reviewing code quality."""

    def __init__(self):
        """Initialize the Code Review Agent."""
        config = AgentConfig(
            name="CodeReviewAgent",
            description="Reviews code for quality, standards, and best practices",
            phase=Phase.CODE_REVIEW,
            system_prompt=CODE_REVIEW_SYSTEM_PROMPT,
            temperature=0.3,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context with code to review."""
        parts = ["## Code to Review"]

        # Get artifacts that haven't been reviewed (or recently added)
        for artifact in state.code_artifacts:
            parts.append(f"\n### {artifact.file_path}\n```{artifact.language}")
            parts.append(artifact.content)
            parts.append("```")

        # Include architecture context for reference
        if state.system_design:
            parts.append(f"\n## Architecture Context\n{state.system_design[:1000]}...")

        # Current story context
        current_story = state.get_current_story()
        if not current_story:
            # Find story in review
            for epic in state.epics:
                for story in epic.stories:
                    if story.status == StoryStatus.IN_REVIEW:
                        current_story = story
                        break

        if current_story:
            parts.append(f"\n## Story Being Implemented\n{current_story.title}\n{current_story.description}")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the review response and create comments."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                review = json.loads(content.strip())
            else:
                review = {}

            # Create review comments
            for comment_data in review.get("comments", []):
                # Map file path to artifact
                file_path = comment_data.get("file_path", "")
                artifact_id = None
                for artifact in state.code_artifacts:
                    if artifact.file_path == file_path:
                        artifact_id = artifact.id
                        break

                severity_str = comment_data.get("severity", "info").lower()
                severity = Severity(severity_str) if severity_str in Severity.__members__.values() else Severity.INFO

                comment = CodeReviewComment(
                    artifact_id=artifact_id or state.code_artifacts[-1].id if state.code_artifacts else None,
                    line_number=comment_data.get("line_number"),
                    comment=comment_data.get("comment", ""),
                    severity=severity,
                )
                state.review_comments.append(comment)

            # Update approval status
            state.review_approved = review.get("approved", False)

            # Update story status based on review
            current_story = None
            for epic in state.epics:
                for story in epic.stories:
                    if story.status == StoryStatus.IN_REVIEW:
                        current_story = story
                        break

            if current_story:
                if state.review_approved:
                    current_story.status = StoryStatus.TESTING
                else:
                    current_story.status = StoryStatus.IN_PROGRESS  # Back to development

            self.logger.info(
                "Code review completed",
                comments_count=len(review.get("comments", [])),
                approved=state.review_approved,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse review JSON", error=str(e))
            state.errors.append(f"Review parsing error: {str(e)}")

        return state
