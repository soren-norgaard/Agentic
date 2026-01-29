# =============================================================================
# SDLC Agent - Developer Agent
# =============================================================================
# Agent responsible for writing code based on specifications.
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
class DeveloperState(AgentState):
    """State specific to the developer agent."""

    # Current implementation context
    current_story: dict[str, Any] | None = None
    architecture_context: dict[str, Any] | None = None

    # Code context
    existing_files: list[dict[str, Any]] = field(default_factory=list)
    modified_files: list[dict[str, Any]] = field(default_factory=list)
    new_files: list[dict[str, Any]] = field(default_factory=list)

    # Implementation tracking
    implementation_plan: list[dict[str, Any]] = field(default_factory=list)
    current_step: int = 0


class DeveloperAgent(BaseAgent[DeveloperState]):
    """
    Developer agent that writes code based on specifications.

    Responsibilities:
    - Understand story requirements and acceptance criteria
    - Follow architectural guidelines
    - Write clean, well-documented code
    - Create appropriate file structure
    - Follow coding standards and best practices
    """

    name = "developer"
    description = "Writes code based on specifications and architectural guidelines"
    phase = AgentPhase.DEVELOPMENT

    @property
    def system_prompt(self) -> str:
        return """You are the Developer Agent, an expert software engineer responsible for implementing features.

Your responsibilities:
1. Understand the story requirements and acceptance criteria
2. Follow the architectural guidelines and patterns
3. Write clean, well-documented, and testable code
4. Create appropriate file structures
5. Follow coding standards and best practices
6. Consider edge cases and error handling

Coding principles:
- Write self-documenting code with clear naming
- Follow SOLID principles
- Keep functions small and focused
- Add appropriate comments for complex logic
- Include type hints (for Python) or types (for TypeScript)
- Handle errors gracefully
- Think about security implications
- Consider performance implications

Before writing code:
1. Review the story and acceptance criteria
2. Understand the architectural context
3. Plan the implementation steps
4. Identify dependencies and interfaces

After writing code:
1. Review for correctness
2. Check for edge cases
3. Ensure proper error handling
4. Verify it meets acceptance criteria

Always explain your implementation decisions and any trade-offs made."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read the contents of an existing file",
                parameters=[
                    ToolParameter(
                        name="file_path",
                        description="Path to the file to read",
                    ),
                ],
            ),
            ToolDefinition(
                name="write_file",
                description="Write content to a file (creates or overwrites)",
                parameters=[
                    ToolParameter(
                        name="file_path",
                        description="Path to the file to write",
                    ),
                    ToolParameter(
                        name="content",
                        description="Content to write to the file",
                    ),
                    ToolParameter(
                        name="description",
                        description="Description of what this file does",
                    ),
                ],
            ),
            ToolDefinition(
                name="modify_file",
                description="Modify specific sections of an existing file",
                parameters=[
                    ToolParameter(
                        name="file_path",
                        description="Path to the file to modify",
                    ),
                    ToolParameter(
                        name="modifications",
                        description="JSON array of modifications: [{search: str, replace: str}]",
                    ),
                    ToolParameter(
                        name="reason",
                        description="Reason for the modifications",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_implementation_plan",
                description="Create a step-by-step implementation plan",
                parameters=[
                    ToolParameter(
                        name="steps",
                        description="JSON array of implementation steps",
                    ),
                ],
            ),
            ToolDefinition(
                name="mark_step_complete",
                description="Mark an implementation step as complete",
                parameters=[
                    ToolParameter(
                        name="step_index",
                        description="Index of the step to mark complete",
                        type="integer",
                    ),
                    ToolParameter(
                        name="notes",
                        description="Notes about the completion",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="request_clarification",
                description="Request clarification on requirements",
                parameters=[
                    ToolParameter(
                        name="question",
                        description="The clarification question",
                    ),
                    ToolParameter(
                        name="context",
                        description="Context for the question",
                    ),
                ],
            ),
            ToolDefinition(
                name="report_blocker",
                description="Report a blocking issue",
                parameters=[
                    ToolParameter(
                        name="issue",
                        description="Description of the blocking issue",
                    ),
                    ToolParameter(
                        name="suggested_resolution",
                        description="Suggested way to resolve the issue",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_story",
                description="Mark the current story as implemented",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of the implementation",
                    ),
                    ToolParameter(
                        name="files_created",
                        description="JSON array of files created",
                    ),
                    ToolParameter(
                        name="files_modified",
                        description="JSON array of files modified",
                    ),
                ],
            ),
        ]

    async def process(self, state: DeveloperState) -> DeveloperState:
        """Process the current state and implement code."""
        state.iteration_count += 1
        self.logger.info(
            "Developer processing",
            iteration=state.iteration_count,
            story=state.current_story.get("id") if state.current_story else None,
            step=state.current_step,
        )

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for msg in state.messages[-10:]:
            messages.append(msg.to_dict())

        # Build context
        context_parts = ["Current Context:"]

        if state.current_story:
            context_parts.append(f"\nStory: {state.current_story.get('title')}")
            context_parts.append(f"Description: {state.current_story.get('description')}")
            context_parts.append(
                f"Acceptance Criteria: {state.current_story.get('acceptance_criteria')}"
            )

        if state.architecture_context:
            context_parts.append(f"\nArchitecture: {state.architecture_context}")

        if state.implementation_plan:
            context_parts.append(f"\nImplementation Plan ({state.current_step + 1}/{len(state.implementation_plan)}):")
            for i, step in enumerate(state.implementation_plan):
                status = "✓" if step.get("complete") else "○"
                marker = "→" if i == state.current_step else " "
                context_parts.append(f"  {marker} {status} {step.get('description')}")

        if state.existing_files:
            context_parts.append(f"\nExisting Files: {[f.get('path') for f in state.existing_files]}")

        if state.new_files:
            context_parts.append(f"\nNew Files Created: {[f.get('path') for f in state.new_files]}")

        context_parts.append("\nWhat should we implement next?")

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
        self, state: DeveloperState, tool_call: dict[str, Any]
    ) -> None:
        """Handle a tool call from the LLM."""
        import json

        name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        self.logger.info("Handling tool call", tool=name)

        if name == "write_file":
            file_info = {
                "path": args.get("file_path"),
                "content": args.get("content"),
                "description": args.get("description"),
            }
            state.new_files.append(file_info)
            state.add_artifact(
                name=args.get("file_path"),
                artifact_type="code",
                content=args.get("content"),
                description=args.get("description"),
            )

        elif name == "modify_file":
            modification = {
                "path": args.get("file_path"),
                "modifications": json.loads(args.get("modifications", "[]")),
                "reason": args.get("reason"),
            }
            state.modified_files.append(modification)

        elif name == "create_implementation_plan":
            steps = json.loads(args.get("steps", "[]"))
            state.implementation_plan = [
                {"description": s, "complete": False} for s in steps
            ]
            state.current_step = 0

        elif name == "mark_step_complete":
            step_index = args.get("step_index", 0)
            if 0 <= step_index < len(state.implementation_plan):
                state.implementation_plan[step_index]["complete"] = True
                state.implementation_plan[step_index]["notes"] = args.get("notes")
                # Move to next step
                if step_index == state.current_step:
                    state.current_step = min(
                        state.current_step + 1, len(state.implementation_plan) - 1
                    )

        elif name == "request_clarification":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "clarification",
                "question": args.get("question"),
                "context": args.get("context"),
            }

        elif name == "report_blocker":
            state.add_error(
                "blocker",
                args.get("issue"),
                suggested_resolution=args.get("suggested_resolution"),
            )
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "blocker",
                "issue": args.get("issue"),
                "suggested_resolution": args.get("suggested_resolution"),
            }

        elif name == "complete_story":
            if state.current_story:
                state.current_story["status"] = "implemented"
                state.current_story["implementation_summary"] = args.get("summary")
                state.completed_tasks.append(state.current_story)
                state.current_task = None
