# =============================================================================
# SDLC Agent - Requirements Agent
# =============================================================================
# Analyzes requirements and creates epics/stories.
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
class RequirementsState(AgentState):
    """State specific to the requirements agent."""

    # Requirements artifacts
    functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    non_functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    epics: list[dict[str, Any]] = field(default_factory=list)
    user_stories: list[dict[str, Any]] = field(default_factory=list)
    acceptance_criteria: list[dict[str, Any]] = field(default_factory=list)


class RequirementsAgent(BaseAgent[RequirementsState]):
    """
    Requirements analysis agent.

    Responsibilities:
    - Parse and understand project objectives
    - Extract functional and non-functional requirements
    - Create epics and user stories
    - Define acceptance criteria
    - Identify ambiguities and request clarification
    """

    name = "requirements"
    description = "Analyzes requirements and creates epics/stories"
    phase = AgentPhase.REQUIREMENTS

    @property
    def system_prompt(self) -> str:
        return """You are a Requirements Analyst Agent specializing in software requirements engineering.

Your responsibilities:
1. Analyze project objectives and extract clear requirements
2. Distinguish between functional and non-functional requirements
3. Create well-defined epics and user stories following best practices
4. Write clear, testable acceptance criteria
5. Identify ambiguities, gaps, or conflicts in requirements
6. Request clarification when needed

When creating user stories, follow this format:
- As a [user type], I want [goal] so that [benefit]

For acceptance criteria, use Given-When-Then format:
- Given [context], When [action], Then [expected result]

Be thorough and systematic. Ask clarifying questions if the requirements are unclear.
Prioritize requirements based on business value and dependencies."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_requirement",
                description="Create a functional or non-functional requirement",
                parameters=[
                    ToolParameter(
                        name="type",
                        description="Type of requirement",
                        enum=["functional", "non_functional"],
                    ),
                    ToolParameter(
                        name="title",
                        description="Short title for the requirement",
                    ),
                    ToolParameter(
                        name="description",
                        description="Detailed description",
                    ),
                    ToolParameter(
                        name="priority",
                        description="Priority level",
                        enum=["critical", "high", "medium", "low"],
                    ),
                ],
            ),
            ToolDefinition(
                name="create_epic",
                description="Create an epic (large feature or initiative)",
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
                        name="business_value",
                        description="Business value statement",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_user_story",
                description="Create a user story",
                parameters=[
                    ToolParameter(
                        name="epic_id",
                        description="ID of the parent epic",
                        required=False,
                    ),
                    ToolParameter(
                        name="title",
                        description="Story title",
                    ),
                    ToolParameter(
                        name="as_a",
                        description="User role (As a...)",
                    ),
                    ToolParameter(
                        name="i_want",
                        description="Goal (I want...)",
                    ),
                    ToolParameter(
                        name="so_that",
                        description="Benefit (So that...)",
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="List of acceptance criteria (JSON array)",
                    ),
                ],
            ),
            ToolDefinition(
                name="request_clarification",
                description="Request clarification on ambiguous requirements",
                parameters=[
                    ToolParameter(
                        name="question",
                        description="The clarifying question",
                    ),
                    ToolParameter(
                        name="context",
                        description="Context about why this clarification is needed",
                    ),
                    ToolParameter(
                        name="options",
                        description="Suggested options if applicable (JSON array)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_requirements",
                description="Mark requirements analysis as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of requirements gathered",
                    ),
                ],
            ),
        ]

    async def process(self, state: RequirementsState) -> RequirementsState:
        """Process requirements analysis."""
        self.logger.info("Requirements agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents (orchestrator) - each agent starts fresh
        state.messages = []
        
        # Get objective from state or metadata
        objective = getattr(state, 'objective', None) or state.metadata.get("objective", "No objective provided")
        state.add_message(
            MessageRole.USER,
            f"Please analyze the following project requirements and create epics and user stories:\n\n{objective}",
        )
        
        # Run with tools
        state = await self.run_with_tools(state)
        
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: RequirementsState,
    ) -> tuple[str, RequirementsState]:
        """Execute requirements tools."""
        import json
        import uuid as uuid_module
        from sdlc_agent.services.task_service import TaskService
        
        # Get project_id from state metadata
        project_id = state.metadata.get("project_id")
        workflow_id = state.workflow_id
        
        if tool_name == "create_requirement":
            req_id = str(uuid_module.uuid4())[:8]
            requirement = {
                "id": req_id,
                "type": tool_args.get("type"),
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "priority": tool_args.get("priority"),
            }
            
            if tool_args.get("type") == "functional":
                state.functional_requirements.append(requirement)
            else:
                state.non_functional_requirements.append(requirement)
            
            state.add_artifact(
                name=f"REQ-{req_id}",
                artifact_type="requirement",
                content=json.dumps(requirement),
            )
            
            return f"Created requirement REQ-{req_id}: {tool_args.get('title')}", state
        
        elif tool_name == "create_epic":
            epic_id = str(uuid_module.uuid4())[:8]
            epic = {
                "id": epic_id,
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "business_value": tool_args.get("business_value"),
                "stories": [],
            }
            state.epics.append(epic)
            
            # Persist to database if we have project_id
            db_epic = None
            if project_id:
                try:
                    db_epic = await TaskService.create_epic(
                        project_id=uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id,
                        title=tool_args.get("title", "Untitled Epic"),
                        description=tool_args.get("description"),
                        business_value=tool_args.get("business_value"),
                        workflow_id=uuid_module.UUID(workflow_id) if workflow_id else None,
                    )
                    epic["db_id"] = str(db_epic.id)
                except Exception as e:
                    self.logger.warning("Failed to persist epic to database", error=str(e))
            
            state.add_artifact(
                name=f"EPIC-{epic_id}",
                artifact_type="epic",
                content=json.dumps(epic),
            )
            
            return f"Created epic EPIC-{epic_id}: {tool_args.get('title')}", state
        
        elif tool_name == "create_user_story":
            story_id = str(uuid_module.uuid4())[:8]
            
            # Parse acceptance criteria
            ac = tool_args.get("acceptance_criteria", "[]")
            if isinstance(ac, str):
                try:
                    ac = json.loads(ac)
                except json.JSONDecodeError:
                    ac = [ac]
            
            story = {
                "id": story_id,
                "epic_id": tool_args.get("epic_id"),
                "title": tool_args.get("title"),
                "user_story": f"As a {tool_args.get('as_a')}, I want {tool_args.get('i_want')} so that {tool_args.get('so_that')}",
                "acceptance_criteria": ac,
            }
            state.user_stories.append(story)
            
            # Link to epic if provided
            epic_id_ref = tool_args.get("epic_id")
            parent_db_id = None
            if epic_id_ref:
                for epic in state.epics:
                    if epic["id"] == epic_id_ref:
                        epic["stories"].append(story_id)
                        parent_db_id = epic.get("db_id")
                        break
            
            # Persist to database if we have project_id
            if project_id:
                try:
                    db_story = await TaskService.create_story(
                        project_id=uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id,
                        title=tool_args.get("title", "Untitled Story"),
                        parent_id=uuid_module.UUID(parent_db_id) if parent_db_id else None,
                        as_a=tool_args.get("as_a"),
                        i_want=tool_args.get("i_want"),
                        so_that=tool_args.get("so_that"),
                        acceptance_criteria=ac,
                        workflow_id=uuid_module.UUID(workflow_id) if workflow_id else None,
                    )
                    story["db_id"] = str(db_story.id)
                except Exception as e:
                    self.logger.warning("Failed to persist story to database", error=str(e))
            
            state.add_artifact(
                name=f"STORY-{story_id}",
                artifact_type="user_story",
                content=json.dumps(story),
            )
            
            return f"Created user story STORY-{story_id}: {tool_args.get('title')}", state
        
        elif tool_name == "request_clarification":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "clarification",
                "question": tool_args.get("question"),
                "context": tool_args.get("context"),
                "options": tool_args.get("options"),
            }
            return "Awaiting human clarification", state
        
        elif tool_name == "complete_requirements":
            summary = tool_args.get("summary", "")
            state.add_message(
                MessageRole.ASSISTANT,
                f"Requirements analysis complete.\n\nSummary: {summary}\n\n"
                f"Created {len(state.epics)} epics and {len(state.user_stories)} user stories.",
            )
            state.phase = AgentPhase.PLANNING
            return f"Requirements complete: {len(state.epics)} epics, {len(state.user_stories)} stories", state
        
        return f"Unknown tool: {tool_name}", state
