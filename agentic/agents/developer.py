"""Developer Agent - Implements code based on stories and architecture."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import CodeArtifact, Phase, SDLCState, StoryStatus


DEVELOPER_SYSTEM_PROMPT = """You are a Senior Developer Agent specialized in writing clean, maintainable code.

Your responsibilities:
1. Implement user stories according to the architecture design
2. Write clean, well-documented code following best practices
3. Follow the established coding standards and patterns
4. Implement proper error handling
5. Write code that is testable and modular
6. Consider edge cases and input validation

Output your implementation in the following JSON format:
{
    "files": [
        {
            "file_path": "src/path/to/file.py",
            "content": "The complete file content",
            "language": "python",
            "description": "What this file does"
        }
    ],
    "implementation_notes": "Any notes about the implementation",
    "story_completed": true/false,
    "remaining_work": ["List of any remaining work if story not completed"]
}

Coding Standards:
- Follow language-specific conventions (PEP 8 for Python, etc.)
- Use meaningful variable and function names
- Add docstrings/comments for complex logic
- Keep functions small and focused
- Apply DRY (Don't Repeat Yourself) principle
- Include type hints where applicable
- Handle errors gracefully"""


class DeveloperAgent(BaseAgent):
    """Agent for implementing code based on stories."""

    def __init__(self):
        """Initialize the Developer Agent."""
        config = AgentConfig(
            name="DeveloperAgent",
            description="Implements code based on user stories and architecture",
            phase=Phase.DEVELOPMENT,
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
            temperature=0.2,  # Lower temperature for more consistent code
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context from architecture and current story."""
        parts = []

        # Current story to implement
        current_story = state.get_current_story()
        if current_story:
            parts.append(f"## Current Story\n**{current_story.title}**\n{current_story.description}")
            if current_story.acceptance_criteria:
                parts.append("### Acceptance Criteria")
                for ac in current_story.acceptance_criteria:
                    status = "✓" if ac.is_met else "○"
                    parts.append(f"- [{status}] {ac.description}")
        else:
            # Find next story to work on
            for epic in state.epics:
                for story in epic.stories:
                    if story.status == StoryStatus.REFINED:
                        parts.append(
                            f"## Next Story to Implement\n**{story.title}**\n{story.description}"
                        )
                        if story.acceptance_criteria:
                            parts.append("### Acceptance Criteria")
                            for ac in story.acceptance_criteria:
                                parts.append(f"- {ac.description}")
                        break
                else:
                    continue
                break

        # Architecture context
        if state.system_design:
            parts.append(f"## System Design\n{state.system_design[:2000]}...")  # Truncate if too long

        # Existing code artifacts for reference
        if state.code_artifacts:
            parts.append("## Existing Code Files")
            for artifact in state.code_artifacts[-5:]:  # Last 5 files
                parts.append(f"- {artifact.file_path} ({artifact.language})")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the LLM response and create code artifacts."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                implementation = json.loads(content.strip())
            else:
                implementation = {}

            # Get current story for linking
            current_story = state.get_current_story()
            story_id = current_story.id if current_story else None

            # Create code artifacts
            for file_data in implementation.get("files", []):
                artifact = CodeArtifact(
                    file_path=file_data.get("file_path", "unknown"),
                    content=file_data.get("content", ""),
                    language=file_data.get("language", "text"),
                    story_id=story_id,
                )
                state.code_artifacts.append(artifact)

            # Update story status if completed
            if implementation.get("story_completed", False) and current_story:
                current_story.status = StoryStatus.IN_REVIEW

            self.logger.info(
                "Code implemented",
                files_count=len(implementation.get("files", [])),
                story_completed=implementation.get("story_completed", False),
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse developer JSON", error=str(e))
            state.errors.append(f"Developer parsing error: {str(e)}")

        return state
