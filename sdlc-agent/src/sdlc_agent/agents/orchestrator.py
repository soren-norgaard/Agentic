# =============================================================================
# SDLC Agent - Orchestrator Agent
# =============================================================================
# The main supervisor agent that coordinates all other agents.
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
class OrchestratorState(AgentState):
    """State specific to the orchestrator."""

    # Objective tracking
    objective: str = ""
    epics: list[dict[str, Any]] = field(default_factory=list)
    stories: list[dict[str, Any]] = field(default_factory=list)

    # Phase management
    phases_completed: list[str] = field(default_factory=list)
    current_agent: str | None = None

    # Decision history
    decisions: list[dict[str, Any]] = field(default_factory=list)


class OrchestratorAgent(BaseAgent[OrchestratorState]):
    """
    Main orchestrator agent that coordinates the SDLC workflow.

    Responsibilities:
    - Parse and understand the project objective
    - Break down into epics and stories
    - Route work to appropriate specialized agents
    - Track progress and handle handoffs
    - Request human approval at critical gates
    """

    name = "orchestrator"
    description = "Coordinates the entire SDLC workflow"
    phase = AgentPhase.REQUIREMENTS

    @property
    def system_prompt(self) -> str:
        return """You are the SDLC Orchestrator Agent, responsible for coordinating the entire software development lifecycle.

Your responsibilities:
1. Understand project objectives and requirements
2. Break down work into epics, stories, and tasks
3. Delegate work to specialized agents (Requirements, Planning, Development, Testing, Security, DevOps)
4. Track progress and ensure quality gates are met
5. Request human approval at critical decision points

You have access to the following specialized agents:
- requirements_agent: Analyzes and refines requirements, creates acceptance criteria
- planning_agent: Breaks epics into stories, estimates complexity, creates sprint plans
- architect_agent: Designs system architecture, defines APIs and patterns
- developer_agent: Writes code, implements features
- code_review_agent: Reviews code for quality, security, and best practices
- tester_agent: Creates and runs tests, validates functionality
- security_agent: Performs security analysis and vulnerability scanning
- devops_agent: Manages CI/CD, deployment, and infrastructure

Quality Gates (require human approval):
- Epic/story breakdown approval
- Architecture design approval
- PR/code merge approval
- Deployment to production approval

Always maintain clear communication about:
- Current phase and progress
- Any blockers or issues
- Decisions that need human input

Be methodical, thorough, and always prioritize quality over speed."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="delegate_to_agent",
                description="Delegate a task to a specialized agent",
                parameters=[
                    ToolParameter(
                        name="agent_name",
                        description="Name of the agent to delegate to",
                        enum=[
                            "requirements_agent",
                            "planning_agent",
                            "architect_agent",
                            "developer_agent",
                            "code_review_agent",
                            "tester_agent",
                            "security_agent",
                            "devops_agent",
                        ],
                    ),
                    ToolParameter(
                        name="task",
                        description="Description of the task to delegate",
                    ),
                    ToolParameter(
                        name="context",
                        description="Additional context for the task",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="request_human_approval",
                description="Request approval from a human for a critical decision",
                parameters=[
                    ToolParameter(
                        name="approval_type",
                        description="Type of approval needed",
                        enum=["epic_breakdown", "architecture", "code_merge", "deployment"],
                    ),
                    ToolParameter(
                        name="description",
                        description="Description of what needs approval",
                    ),
                    ToolParameter(
                        name="options",
                        description="Options for the human to choose from (JSON array)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="create_epic",
                description="Create a new epic from the objective",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Epic title",
                    ),
                    ToolParameter(
                        name="description",
                        description="Epic description",
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="Acceptance criteria (JSON array of strings)",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_story",
                description="Create a user story within an epic",
                parameters=[
                    ToolParameter(
                        name="epic_id",
                        description="ID of the parent epic",
                    ),
                    ToolParameter(
                        name="title",
                        description="Story title",
                    ),
                    ToolParameter(
                        name="description",
                        description="Story description (as a user...)",
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="Acceptance criteria (JSON array of strings)",
                    ),
                    ToolParameter(
                        name="story_points",
                        description="Estimated story points",
                        type="integer",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="update_phase",
                description="Update the current SDLC phase",
                parameters=[
                    ToolParameter(
                        name="phase",
                        description="New phase to transition to",
                        enum=[
                            "requirements",
                            "planning",
                            "design",
                            "development",
                            "code_review",
                            "testing",
                            "security",
                            "deployment",
                            "monitoring",
                        ],
                    ),
                    ToolParameter(
                        name="reason",
                        description="Reason for phase transition",
                    ),
                ],
            ),
            ToolDefinition(
                name="report_progress",
                description="Report progress on the current workflow",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of current progress",
                    ),
                    ToolParameter(
                        name="completed_items",
                        description="List of completed items (JSON array)",
                        required=False,
                    ),
                    ToolParameter(
                        name="pending_items",
                        description="List of pending items (JSON array)",
                        required=False,
                    ),
                    ToolParameter(
                        name="blockers",
                        description="Any blockers (JSON array)",
                        required=False,
                    ),
                ],
            ),
        ]

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process the current state and coordinate the workflow."""
        state.iteration_count += 1
        self.logger.info(
            "Orchestrator processing",
            iteration=state.iteration_count,
            phase=state.phase.value,
            current_agent=state.current_agent,
        )

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for msg in state.messages[-10:]:  # Keep last 10 messages for context
            messages.append(msg.to_dict())

        # Add current state context
        context = f"""
Current State:
- Phase: {state.phase.value}
- Objective: {state.objective}
- Epics: {len(state.epics)}
- Stories: {len(state.stories)}
- Completed Tasks: {len(state.completed_tasks)}
- Pending Tasks: {len(state.task_queue)}
- Artifacts: {len(state.artifacts)}
- Errors: {len(state.errors)}

What should we do next?
"""
        messages.append({"role": "user", "content": context})

        # Call LLM
        tools = [t.to_openai_schema() for t in self.tools]
        response = await self._call_llm(messages, tools)

        # Process response
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        # Add response to messages
        state.add_message(MessageRole.ASSISTANT, content)

        # Process tool calls
        if tool_calls:
            for tool_call in tool_calls:
                await self._handle_tool_call(state, tool_call)

        return state

    async def _handle_tool_call(
        self, state: OrchestratorState, tool_call: dict[str, Any]
    ) -> None:
        """Handle a tool call from the LLM."""
        import json

        name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        self.logger.info("Handling tool call", tool=name, args=args)

        if name == "delegate_to_agent":
            state.current_agent = args.get("agent_name")
            state.task_queue.append(
                {
                    "agent": args.get("agent_name"),
                    "task": args.get("task"),
                    "context": args.get("context"),
                    "status": "pending",
                }
            )
            state.decisions.append(
                {
                    "type": "delegation",
                    "agent": args.get("agent_name"),
                    "task": args.get("task"),
                }
            )

        elif name == "request_human_approval":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": args.get("approval_type"),
                "description": args.get("description"),
                "options": json.loads(args.get("options", "[]")),
            }

        elif name == "create_epic":
            epic = {
                "id": f"epic-{len(state.epics) + 1}",
                "title": args.get("title"),
                "description": args.get("description"),
                "acceptance_criteria": json.loads(
                    args.get("acceptance_criteria", "[]")
                ),
                "status": "open",
            }
            state.epics.append(epic)

        elif name == "create_story":
            story = {
                "id": f"story-{len(state.stories) + 1}",
                "epic_id": args.get("epic_id"),
                "title": args.get("title"),
                "description": args.get("description"),
                "acceptance_criteria": json.loads(
                    args.get("acceptance_criteria", "[]")
                ),
                "story_points": args.get("story_points"),
                "status": "backlog",
            }
            state.stories.append(story)

        elif name == "update_phase":
            new_phase = AgentPhase(args.get("phase"))
            state.phases_completed.append(state.phase.value)
            state.phase = new_phase
            state.decisions.append(
                {
                    "type": "phase_transition",
                    "from": state.phases_completed[-1],
                    "to": new_phase.value,
                    "reason": args.get("reason"),
                }
            )

        elif name == "report_progress":
            state.metadata["last_progress_report"] = {
                "summary": args.get("summary"),
                "completed": json.loads(args.get("completed_items", "[]")),
                "pending": json.loads(args.get("pending_items", "[]")),
                "blockers": json.loads(args.get("blockers", "[]")),
            }

    def get_next_agent(self, state: OrchestratorState) -> str | None:
        """Determine the next agent based on delegation."""
        if state.current_agent:
            return state.current_agent
        return None
