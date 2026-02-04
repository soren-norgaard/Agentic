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


def get_phase_value(phase: Any) -> str:
    """Safely get string value from phase (handles both enum and string)."""
    if hasattr(phase, "value"):
        return phase.value
    return str(phase) if phase else "unknown"


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
    
    # Workflow control
    workflow_complete: bool = False


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

Your PRIMARY responsibility is to DELEGATE work to specialized agents. You should NOT do the detailed work yourself.

## Workflow Process (MUST follow in order):
1. **Requirements Phase**: DELEGATE to requirements_agent to analyze requirements and create epics/stories
2. **Planning Phase**: DELEGATE to planning_agent to create implementation plans and tasks
3. **Development Phase**: DELEGATE to developer_agent to prepare developer briefs for implementation
4. **Code Review Phase**: DELEGATE to code_review_agent to review code
5. **Testing Phase**: DELEGATE to tester_agent to create and run tests
6. **Security Phase**: DELEGATE to security_agent to perform security analysis
7. **Deployment Phase**: DELEGATE to devops_agent to handle deployment

## CRITICAL RULES:
- ALWAYS progress through ALL phases in order
- Use delegate_to_agent to hand off work to specialized agents
- Do NOT skip phases - each phase must be executed
- Do NOT call complete_workflow until ALL phases are done
- After requirements is done, delegate to planning
- After planning is done, delegate to developer
- After development is done, delegate to code_review (or testing if no code)
- Only complete_workflow when deployment is finished

## Available Agents:
- requirements_agent: Analyzes requirements, creates epics and user stories
- planning_agent: Creates implementation plans, breaks down stories into tasks
- developer_agent: Prepares developer briefs with implementation guidance
- code_review_agent: Reviews code for quality and best practices
- tester_agent: Creates and runs tests
- security_agent: Performs security analysis
- devops_agent: Manages deployment and infrastructure

Start by delegating to requirements_agent to analyze the objective."""

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
            ToolDefinition(
                name="complete_workflow",
                description="Mark the entire workflow as complete. Only call this when ALL phases are done.",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of what was accomplished",
                    ),
                    ToolParameter(
                        name="deliverables",
                        description="List of deliverables produced (JSON array)",
                    ),
                ],
            ),
        ]

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process the current state and coordinate the workflow."""
        state.iteration_count += 1
        
        # Safety limit - max 50 iterations
        if state.iteration_count >= 50:
            self.logger.warning("Max iterations reached, completing workflow")
            state.workflow_complete = True
            state.metadata["workflow_summary"] = {
                "summary": "Workflow ended due to max iterations limit",
                "deliverables": [],
            }
            return state
        
        self.logger.info(
            "Orchestrator processing",
            iteration=state.iteration_count,
            phase=get_phase_value(state.phase),
            current_agent=state.current_agent,
        )

        # Clear messages from previous agents - orchestrator starts fresh each time
        # This avoids null content errors from tool-call-only assistant messages
        state.messages = []

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Track which phases have been completed
        phases_done = state.phases_completed if hasattr(state, 'phases_completed') else []
        agent_history = state.agent_history if hasattr(state, 'agent_history') else []
        
        # Determine what work has been done
        requirements_done = len(state.epics) > 0 and len(state.user_stories) > 0
        # Planning is done if we have tasks OR if 'planning' is in phases_completed
        planning_done = len(state.tasks) > 0 or 'planning' in phases_done
        # Test stubs generated (TDD - after planning, before development)
        test_stubs_generated = getattr(state, 'test_stubs_generated', False) or len(getattr(state, 'test_stubs', [])) > 0
        # Development is done if we have developer briefs OR 'development' in phases_completed
        development_done = (len(state.code_files) > 0 if hasattr(state, 'code_files') else False) or 'development' in phases_done
        testing_done = (len(state.test_results) > 0 if hasattr(state, 'test_results') else False) or 'testing' in phases_done
        
        # Add current state context
        context = f"""
Current State:
- Phase: {get_phase_value(state.phase)}
- Iteration: {state.iteration_count}/50
- Objective: {state.objective}

Progress:
- Requirements Complete: {requirements_done} (Epics: {len(state.epics)}, User Stories: {len(getattr(state, 'user_stories', []))}, Stories: {len(state.stories)})
- Planning Complete: {planning_done} (Tasks: {len(getattr(state, 'tasks', []))}, Milestones: {len(getattr(state, 'milestones', []))})
- Test Stubs Generated: {test_stubs_generated} (TDD - Stubs: {len(getattr(state, 'test_stubs', []))})
- Development Complete: {development_done} (Code Files: {len(getattr(state, 'code_files', {}))})
- Testing Complete: {testing_done} (Tests: {len(getattr(state, 'test_results', []))})

Phases Completed: {phases_done}
Agent History: {agent_history[-5:] if agent_history else []}
Pending Tasks: {len(state.task_queue)}
Errors: {len(state.errors)}

## NEXT ACTION REQUIRED (TDD Workflow):
- If requirements NOT done: delegate to requirements_agent
- If requirements done but planning NOT done: delegate to planning_agent
- If planning done but test stubs NOT generated: delegate to tester_agent (with stub_mode=true)
- If test stubs generated but development NOT done: delegate to developer_agent
- If development done but testing NOT done: delegate to tester_agent (full testing mode)
- Continue until ALL phases complete, then use complete_workflow

Do NOT skip phases. TDD means we generate test stubs BEFORE development. What agent should we delegate to next?
"""
        messages.append({"role": "user", "content": context})

        # Call LLM
        tools = [t.to_openai_schema() for t in self.tools]
        
        # Filter out any messages with null content before calling LLM
        filtered_messages = []
        for msg in messages:
            content = msg.get("content")
            # Skip messages with null content (tool-call-only assistant messages)
            if msg.get("role") == "assistant" and content is None:
                continue
            # Ensure content is not None
            if content is None:
                msg["content"] = ""
            filtered_messages.append(msg)
        
        response = await self._call_llm(filtered_messages, tools)

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
            current_phase_value = get_phase_value(state.phase)
            # Only add to phases_completed if not already there (prevent duplicates)
            if current_phase_value not in state.phases_completed:
                state.phases_completed.append(current_phase_value)
            state.phase = new_phase
            state.decisions.append(
                {
                    "type": "phase_transition",
                    "from": current_phase_value,
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

        elif name == "complete_workflow":
            state.workflow_complete = True
            state.metadata["workflow_summary"] = {
                "summary": args.get("summary"),
                "deliverables": json.loads(args.get("deliverables", "[]")),
            }
            self.logger.info("Workflow marked as complete", summary=args.get("summary"))

    def get_next_agent(self, state: OrchestratorState) -> str | None:
        """Determine the next agent based on delegation."""
        if state.current_agent:
            return state.current_agent
        return None
