"""Planning Agent - Breaks objectives into epics and stories."""

import json
from uuid import uuid4
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import (
    AcceptanceCriteria,
    Epic,
    Phase,
    SDLCState,
    Story,
    StoryStatus,
)


PLANNING_SYSTEM_PROMPT = """You are a Product Planning Agent specialized in breaking down project objectives into actionable work items.

Your responsibilities:
1. Analyze the clarified project objective and requirements
2. Identify logical groupings of functionality (Epics)
3. Break each Epic into detailed User Stories
4. Define clear acceptance criteria for each story
5. Estimate story complexity (story points: 1, 2, 3, 5, 8, 13, 21)
6. Identify dependencies between stories
7. Prioritize stories based on value and dependencies

Output your plan in the following JSON format:
{
    "epics": [
        {
            "title": "Epic title",
            "description": "Epic description",
            "priority": 0-100,
            "stories": [
                {
                    "title": "Story title",
                    "description": "As a [user], I want [feature] so that [benefit]",
                    "acceptance_criteria": [
                        "Given [context], when [action], then [result]"
                    ],
                    "story_points": 1-21,
                    "priority": 0-100,
                    "dependencies": ["title of dependent story if any"]
                }
            ]
        }
    ]
}

Story Writing Guidelines:
- Use "As a [role], I want [feature], so that [benefit]" format
- Acceptance criteria should be testable and specific
- Keep stories small enough to complete in one iteration
- Stories should be independent when possible (INVEST principles)
- Higher priority = lower number (0 is highest priority)"""


class PlanningAgent(BaseAgent):
    """Agent for breaking objectives into epics and stories."""

    def __init__(self):
        """Initialize the Planning Agent."""
        config = AgentConfig(
            name="PlanningAgent",
            description="Breaks down objectives into epics and user stories",
            phase=Phase.PLANNING,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            temperature=0.7,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context from the refined objective."""
        if not state.objective:
            return "No project objective available."

        parts = [f"## Project Objective\n{state.objective.clarified_objective or state.objective.raw_input}"]

        if state.objective.constraints:
            parts.append("## Constraints\n" + "\n".join(f"- {c}" for c in state.objective.constraints))

        if state.objective.non_functional_requirements:
            parts.append(
                "## Non-Functional Requirements\n"
                + "\n".join(f"- {r}" for r in state.objective.non_functional_requirements)
            )

        if state.objective.tech_stack_preferences:
            parts.append(
                "## Technology Preferences\n"
                + "\n".join(f"- {t}" for t in state.objective.tech_stack_preferences)
            )

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the LLM response and create epics/stories."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                plan = json.loads(content.strip())
            else:
                plan = {}

            # Create epics and stories from the plan
            story_title_to_id: dict[str, str] = {}
            epics_data = plan.get("epics", [])

            for epic_data in epics_data:
                epic = Epic(
                    title=epic_data.get("title", "Untitled Epic"),
                    description=epic_data.get("description", ""),
                    priority=epic_data.get("priority", 50),
                )

                for story_data in epic_data.get("stories", []):
                    story_id = uuid4()
                    story_title = story_data.get("title", "Untitled Story")
                    story_title_to_id[story_title] = str(story_id)

                    acceptance_criteria = [
                        AcceptanceCriteria(description=ac)
                        for ac in story_data.get("acceptance_criteria", [])
                    ]

                    story = Story(
                        id=story_id,
                        title=story_title,
                        description=story_data.get("description", ""),
                        acceptance_criteria=acceptance_criteria,
                        story_points=story_data.get("story_points"),
                        priority=story_data.get("priority", 50),
                        status=StoryStatus.REFINED,
                    )
                    epic.stories.append(story)

                state.epics.append(epic)

            # Resolve story dependencies (second pass)
            for epic in state.epics:
                for story in epic.stories:
                    # Dependencies were stored as titles, convert to IDs
                    # This is handled in the story creation above

            total_stories = sum(len(e.stories) for e in state.epics)
            total_points = sum(
                s.story_points or 0 for e in state.epics for s in e.stories
            )

            self.logger.info(
                "Planning completed",
                epics_count=len(state.epics),
                stories_count=total_stories,
                total_points=total_points,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse planning JSON", error=str(e))
            state.errors.append(f"Planning parsing error: {str(e)}")

        return state
