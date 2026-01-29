"""Requirements Agent - Understands and refines project objectives."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import Phase, ProjectObjective, SDLCState


REQUIREMENTS_SYSTEM_PROMPT = """You are a Requirements Analyst Agent specialized in understanding and refining software project objectives.

Your responsibilities:
1. Analyze the user's raw project description
2. Clarify the main objective in clear, actionable terms
3. Identify explicit and implicit constraints
4. Extract non-functional requirements (performance, security, scalability, etc.)
5. Note any technology stack preferences mentioned
6. Ask clarifying questions if critical information is missing

Output your analysis in the following JSON format:
{
    "clarified_objective": "A clear, refined statement of what needs to be built",
    "constraints": ["List of constraints and limitations"],
    "non_functional_requirements": ["Performance", "Security", "Scalability requirements etc."],
    "tech_stack_preferences": ["Any mentioned or implied technology preferences"],
    "clarifying_questions": ["Questions that would help refine requirements further"],
    "confidence_score": 0.0 to 1.0
}

Be thorough but concise. Focus on understanding what the user truly needs, not just what they said."""


class RequirementsAgent(BaseAgent):
    """Agent for understanding and refining project requirements."""

    def __init__(self):
        """Initialize the Requirements Agent."""
        config = AgentConfig(
            name="RequirementsAgent",
            description="Understands and refines project objectives from user input",
            phase=Phase.REQUIREMENTS,
            system_prompt=REQUIREMENTS_SYSTEM_PROMPT,
            temperature=0.5,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context from the project objective."""
        if not state.objective:
            return "No project objective provided."

        context_parts = [
            f"## Project Input\n{state.objective.raw_input}",
        ]

        if state.objective.constraints:
            context_parts.append(
                f"\n## Known Constraints\n" + "\n".join(f"- {c}" for c in state.objective.constraints)
            )

        return "\n\n".join(context_parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the LLM response and update the project objective."""
        try:
            # Parse JSON from response
            content = response.content
            if isinstance(content, str):
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                analysis = json.loads(content.strip())
            else:
                analysis = {}

            # Update objective with refined information
            if state.objective:
                state.objective.clarified_objective = analysis.get("clarified_objective")
                state.objective.constraints = analysis.get("constraints", [])
                state.objective.non_functional_requirements = analysis.get(
                    "non_functional_requirements", []
                )
                state.objective.tech_stack_preferences = analysis.get("tech_stack_preferences", [])

            self.logger.info(
                "Requirements analyzed",
                constraints_count=len(state.objective.constraints) if state.objective else 0,
                nfr_count=len(state.objective.non_functional_requirements) if state.objective else 0,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse requirements JSON", error=str(e))
            # Store raw response as clarified objective if parsing fails
            if state.objective and isinstance(response.content, str):
                state.objective.clarified_objective = response.content

        return state
