"""Architect Agent - Designs system architecture."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import ArchitectureDecision, Phase, SDLCState


ARCHITECT_SYSTEM_PROMPT = """You are a Software Architect Agent specialized in designing robust, scalable system architectures.

Your responsibilities:
1. Analyze project requirements and constraints
2. Design high-level system architecture
3. Make and document key architecture decisions (ADRs)
4. Define component boundaries and interfaces
5. Select appropriate patterns and technologies
6. Consider non-functional requirements (scalability, security, performance)
7. Create a system design document

Output your architecture in the following JSON format:
{
    "system_design": "A comprehensive description of the system architecture in Markdown format",
    "architecture_decisions": [
        {
            "title": "Decision title (e.g., 'Use PostgreSQL for primary database')",
            "context": "Why this decision was needed",
            "decision": "What was decided",
            "rationale": "Why this option was chosen",
            "consequences": ["List of consequences/tradeoffs"],
            "alternatives_considered": ["Other options that were evaluated"]
        }
    ],
    "components": [
        {
            "name": "Component name",
            "responsibility": "What this component does",
            "technology": "Technology/framework to use",
            "interfaces": ["APIs or interfaces exposed"]
        }
    ],
    "data_model": "Description of key entities and relationships",
    "api_contracts": "High-level API design"
}

Architecture Principles:
- Favor simplicity over complexity
- Design for change and extensibility
- Consider operational concerns (logging, monitoring, deployment)
- Apply SOLID principles
- Use well-known patterns appropriately"""


class ArchitectAgent(BaseAgent):
    """Agent for designing system architecture."""

    def __init__(self):
        """Initialize the Architect Agent."""
        config = AgentConfig(
            name="ArchitectAgent",
            description="Designs system architecture and makes key technical decisions",
            phase=Phase.ARCHITECTURE,
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            temperature=0.5,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context from requirements and stories."""
        parts = []

        if state.objective:
            parts.append(
                f"## Project Objective\n{state.objective.clarified_objective or state.objective.raw_input}"
            )

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

        if state.epics:
            parts.append("## Epics and Stories")
            for epic in state.epics:
                parts.append(f"\n### {epic.title}\n{epic.description}")
                for story in epic.stories:
                    parts.append(f"- {story.title}: {story.description}")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the LLM response and update architecture artifacts."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                architecture = json.loads(content.strip())
            else:
                architecture = {}

            # Store system design
            state.system_design = architecture.get("system_design", "")

            # Create architecture decisions
            for adr_data in architecture.get("architecture_decisions", []):
                adr = ArchitectureDecision(
                    title=adr_data.get("title", ""),
                    context=adr_data.get("context", ""),
                    decision=adr_data.get("decision", ""),
                    rationale=adr_data.get("rationale", ""),
                    consequences=adr_data.get("consequences", []),
                    alternatives_considered=adr_data.get("alternatives_considered", []),
                )
                state.architecture_decisions.append(adr)

            self.logger.info(
                "Architecture designed",
                decisions_count=len(state.architecture_decisions),
                has_system_design=bool(state.system_design),
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse architecture JSON", error=str(e))
            # Store raw response as system design
            if isinstance(response.content, str):
                state.system_design = response.content

        return state
