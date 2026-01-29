# =============================================================================
# SDLC Agent - Planning Agent
# =============================================================================
# Creates implementation plans and breaks down work into tasks.
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
class PlanningState(AgentState):
    """State specific to the planning agent."""

    # Planning artifacts
    technical_plan: dict[str, Any] = field(default_factory=dict)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    milestones: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    estimates: dict[str, int] = field(default_factory=dict)


class PlanningAgent(BaseAgent[PlanningState]):
    """
    Planning and task breakdown agent.

    Responsibilities:
    - Break user stories into implementation tasks
    - Estimate complexity and effort
    - Identify dependencies between tasks
    - Create implementation milestones
    - Suggest technical approaches
    """

    name = "planning"
    description = "Creates implementation plans and task breakdowns"
    phase = AgentPhase.PLANNING

    @property
    def system_prompt(self) -> str:
        return """You are a Technical Planning Agent specializing in software project planning.

Your responsibilities:
1. Break down user stories into concrete implementation tasks
2. Estimate task complexity using story points (1, 2, 3, 5, 8, 13)
3. Identify dependencies between tasks
4. Create logical implementation milestones
5. Suggest technical approaches and architecture decisions

For each task, consider:
- Clear definition of done
- Required skills and expertise
- Potential risks and blockers
- Testing requirements

Order tasks by dependencies and priority. Group related tasks into milestones.
Be specific about what needs to be implemented, not just high-level descriptions."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_task",
                description="Create an implementation task",
                parameters=[
                    ToolParameter(
                        name="story_id",
                        description="ID of the parent user story",
                        required=False,
                    ),
                    ToolParameter(
                        name="title",
                        description="Task title",
                    ),
                    ToolParameter(
                        name="description",
                        description="Detailed task description",
                    ),
                    ToolParameter(
                        name="task_type",
                        description="Type of task",
                        enum=["feature", "bug", "refactor", "test", "docs", "infrastructure"],
                    ),
                    ToolParameter(
                        name="story_points",
                        description="Complexity estimate (1, 2, 3, 5, 8, 13)",
                        enum=["1", "2", "3", "5", "8", "13"],
                    ),
                    ToolParameter(
                        name="skills_required",
                        description="Required skills (JSON array)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="add_dependency",
                description="Add a dependency between tasks",
                parameters=[
                    ToolParameter(
                        name="task_id",
                        description="ID of the dependent task",
                    ),
                    ToolParameter(
                        name="depends_on",
                        description="ID of the task it depends on",
                    ),
                    ToolParameter(
                        name="type",
                        description="Type of dependency",
                        enum=["blocks", "required_for", "related_to"],
                    ),
                ],
            ),
            ToolDefinition(
                name="create_milestone",
                description="Create a project milestone",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Milestone title",
                    ),
                    ToolParameter(
                        name="description",
                        description="Milestone description",
                    ),
                    ToolParameter(
                        name="task_ids",
                        description="IDs of tasks in this milestone (JSON array)",
                    ),
                    ToolParameter(
                        name="order",
                        description="Milestone order (1, 2, 3...)",
                    ),
                ],
            ),
            ToolDefinition(
                name="suggest_architecture",
                description="Suggest technical architecture approach",
                parameters=[
                    ToolParameter(
                        name="component",
                        description="Component or area being designed",
                    ),
                    ToolParameter(
                        name="approach",
                        description="Suggested technical approach",
                    ),
                    ToolParameter(
                        name="rationale",
                        description="Rationale for this approach",
                    ),
                    ToolParameter(
                        name="alternatives",
                        description="Alternative approaches considered (JSON array)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_planning",
                description="Mark planning as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of the implementation plan",
                    ),
                    ToolParameter(
                        name="total_points",
                        description="Total story points estimated",
                    ),
                ],
            ),
        ]

    async def process(self, state: PlanningState) -> PlanningState:
        """Process planning tasks."""
        self.logger.info("Planning agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Get context from state (user_stories is set by requirements agent)
        stories = getattr(state, 'user_stories', []) or state.metadata.get("user_stories", [])
        epics = getattr(state, 'epics', []) or state.metadata.get("epics", [])
        
        context = "Please create an implementation plan for the following user stories:\n\n"
        for story in stories:
            context += f"- {story.get('title', 'Untitled')}: {story.get('user_story', '')}\n"
        
        if not stories and epics:
            context = "Please create an implementation plan for the following epics:\n\n"
            for epic in epics:
                context += f"- {epic.get('title', 'Untitled')}: {epic.get('description', '')}\n"
        elif not stories:
            objective = getattr(state, 'objective', '') or state.metadata.get('objective', '')
            context = f"Please create an implementation plan based on the project requirements:\n\n{objective}"
        
        state.add_message(MessageRole.USER, context)
        
        state = await self.run_with_tools(state)
        
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: PlanningState,
    ) -> tuple[str, PlanningState]:
        """Execute planning tools."""
        import json
        import uuid as uuid_module
        from sdlc_agent.services.task_service import TaskService
        
        # Get project_id from state metadata
        project_id = state.metadata.get("project_id")
        workflow_id = state.workflow_id
        
        if tool_name == "create_task":
            task_id = str(uuid_module.uuid4())[:8]
            
            skills = tool_args.get("skills_required", "[]")
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills)
                except json.JSONDecodeError:
                    skills = []
            
            task = {
                "id": task_id,
                "story_id": tool_args.get("story_id"),
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "type": tool_args.get("task_type"),
                "story_points": int(tool_args.get("story_points", 1)),
                "skills_required": skills,
                "status": "backlog",
            }
            state.tasks.append(task)
            
            # Persist to database if we have project_id
            if project_id:
                try:
                    db_task = await TaskService.create_task(
                        project_id=uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id,
                        title=tool_args.get("title", "Untitled Task"),
                        description=tool_args.get("description"),
                        task_type=tool_args.get("task_type", "task"),
                        story_points=int(tool_args.get("story_points", 1)),
                        skills_required=skills,
                        workflow_id=uuid_module.UUID(workflow_id) if workflow_id else None,
                    )
                    task["db_id"] = str(db_task.id)
                except Exception as e:
                    self.logger.warning("Failed to persist task to database", error=str(e))
            
            state.add_artifact(
                name=f"TASK-{task_id}",
                artifact_type="task",
                content=json.dumps(task),
            )
            
            return f"Created task TASK-{task_id}: {tool_args.get('title')} ({tool_args.get('story_points')} points)", state
        
        elif tool_name == "add_dependency":
            dep = {
                "task_id": tool_args.get("task_id"),
                "depends_on": tool_args.get("depends_on"),
                "type": tool_args.get("type"),
            }
            state.dependencies.append(dep)
            return f"Added dependency: TASK-{dep['task_id']} {dep['type']} TASK-{dep['depends_on']}", state
        
        elif tool_name == "create_milestone":
            milestone_id = str(uuid_module.uuid4())[:8]
            
            task_ids = tool_args.get("task_ids", "[]")
            if isinstance(task_ids, str):
                try:
                    task_ids = json.loads(task_ids)
                except json.JSONDecodeError:
                    task_ids = []
            
            milestone = {
                "id": milestone_id,
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "task_ids": task_ids,
                "order": int(tool_args.get("order", 1)),
            }
            state.milestones.append(milestone)
            
            return f"Created milestone M{tool_args.get('order')}: {tool_args.get('title')} ({len(task_ids)} tasks)", state
        
        elif tool_name == "suggest_architecture":
            if "architecture" not in state.technical_plan:
                state.technical_plan["architecture"] = []
            
            alternatives = tool_args.get("alternatives", "[]")
            if isinstance(alternatives, str):
                try:
                    alternatives = json.loads(alternatives)
                except json.JSONDecodeError:
                    alternatives = []
            
            decision = {
                "component": tool_args.get("component"),
                "approach": tool_args.get("approach"),
                "rationale": tool_args.get("rationale"),
                "alternatives": alternatives,
            }
            state.technical_plan["architecture"].append(decision)
            
            return f"Architecture decision for {tool_args.get('component')}: {tool_args.get('approach')}", state
        
        elif tool_name == "complete_planning":
            total_points = sum(t.get("story_points", 0) for t in state.tasks)
            
            state.technical_plan["summary"] = tool_args.get("summary")
            state.technical_plan["total_points"] = total_points
            state.technical_plan["task_count"] = len(state.tasks)
            state.technical_plan["milestone_count"] = len(state.milestones)
            
            state.add_message(
                MessageRole.ASSISTANT,
                f"Planning complete.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Total: {len(state.tasks)} tasks, {total_points} story points, {len(state.milestones)} milestones.",
            )
            state.phase = AgentPhase.DEVELOPMENT
            
            return f"Planning complete: {len(state.tasks)} tasks, {total_points} points", state
        
        return f"Unknown tool: {tool_name}", state
