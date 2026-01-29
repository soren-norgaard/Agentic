# =============================================================================
# SDLC Agent - Agent Graph (LangGraph)
# =============================================================================
# LangGraph-based workflow that orchestrates all agents.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from sdlc_agent.agents.base import AgentPhase, AgentState
from sdlc_agent.agents.code_review import CodeReviewAgent
from sdlc_agent.agents.developer import DeveloperAgent
from sdlc_agent.agents.devops import DevOpsAgent
from sdlc_agent.agents.orchestrator import OrchestratorAgent
from sdlc_agent.agents.planning import PlanningAgent
from sdlc_agent.agents.requirements import RequirementsAgent
from sdlc_agent.agents.security import SecurityAgent
from sdlc_agent.agents.tester import TestingAgent
from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Graph State (Unified)
# =============================================================================


@dataclass
class SDLCState(AgentState):
    """
    Unified state that combines all agent-specific states.

    This allows seamless handoffs between agents while maintaining
    all necessary context.
    """
    
    # Orchestrator fields
    objective: str = ""
    current_agent: str | None = None
    agent_history: list[str] = field(default_factory=list)
    stories: list[dict[str, Any]] = field(default_factory=list)
    phases_completed: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    
    # Requirements fields
    functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    non_functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    epics: list[dict[str, Any]] = field(default_factory=list)
    user_stories: list[dict[str, Any]] = field(default_factory=list)
    
    # Planning fields
    technical_plan: dict[str, Any] = field(default_factory=dict)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    milestones: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    estimates: dict[str, Any] = field(default_factory=dict)
    
    # Developer fields
    current_story: dict[str, Any] | None = None
    architecture_context: dict[str, Any] | None = None
    existing_files: list[dict[str, Any]] = field(default_factory=list)
    modified_files: list[dict[str, Any]] = field(default_factory=list)
    new_files: list[dict[str, Any]] = field(default_factory=list)
    code_files: dict[str, str] = field(default_factory=dict)
    implementation_plan: list[dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    
    # Code Review fields
    reviews: list[dict[str, Any]] = field(default_factory=list)
    issues_found: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    approval_status: str = "pending"
    
    # Testing fields
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    coverage_report: dict[str, Any] = field(default_factory=dict)
    test_plan: dict[str, Any] = field(default_factory=dict)
    
    # Security fields
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    compliance_checks: list[dict[str, Any]] = field(default_factory=list)
    security_score: float = 0.0
    
    # DevOps fields
    pipeline_config: dict[str, Any] = field(default_factory=dict)
    infrastructure_config: dict[str, Any] = field(default_factory=dict)
    deployments: list[dict[str, Any]] = field(default_factory=list)
    environments: dict[str, dict[str, Any]] = field(default_factory=dict)
    
    # Workflow control
    workflow_complete: bool = False


# =============================================================================
# Node Functions
# =============================================================================


async def orchestrator_node(state: SDLCState) -> SDLCState:
    """Orchestrator agent node."""
    agent = OrchestratorAgent()
    return await agent.process(state)


async def developer_node(state: SDLCState) -> SDLCState:
    """Developer agent node."""
    agent = DeveloperAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("developer_agent")
    return state


async def requirements_node(state: SDLCState) -> SDLCState:
    """Requirements agent node."""
    logger.info("Requirements agent processing")
    agent = RequirementsAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("requirements_agent")
    return state


async def planning_node(state: SDLCState) -> SDLCState:
    """Planning agent node."""
    logger.info("Planning agent processing")
    agent = PlanningAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("planning_agent")
    return state


async def code_review_node(state: SDLCState) -> SDLCState:
    """Code review agent node."""
    logger.info("Code review agent processing")
    agent = CodeReviewAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("code_review_agent")
    return state


async def testing_node(state: SDLCState) -> SDLCState:
    """Testing agent node."""
    logger.info("Testing agent processing")
    agent = TestingAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("tester_agent")
    return state


async def security_node(state: SDLCState) -> SDLCState:
    """Security agent node."""
    logger.info("Security agent processing")
    agent = SecurityAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("security_agent")
    return state


async def devops_node(state: SDLCState) -> SDLCState:
    """DevOps agent node."""
    logger.info("DevOps agent processing")
    agent = DevOpsAgent()
    state = await agent.process(state)
    # Clear current_agent after processing so orchestrator can decide next
    state.current_agent = None
    state.agent_history.append("devops_agent")
    return state


async def human_input_node(state: SDLCState) -> SDLCState:
    """Handle human-in-the-loop interactions."""
    logger.info(
        "Awaiting human input",
        request_type=state.human_input_request.get("type") if state.human_input_request else None,
    )
    # This node will be interrupted by the checkpointer
    # The workflow will resume when human input is provided
    return state


# =============================================================================
# Routing Functions
# =============================================================================


def route_from_orchestrator(
    state: SDLCState,
) -> Literal[
    "requirements",
    "planning",
    "developer",
    "code_review",
    "testing",
    "security",
    "devops",
    "human_input",
    "__end__",
]:
    """Route from orchestrator to the next agent."""
    # Check if awaiting human input
    if state.awaiting_human_input:
        return "human_input"

    # Check current agent delegation
    agent_mapping = {
        "requirements_agent": "requirements",
        "planning_agent": "planning",
        "developer_agent": "developer",
        "code_review_agent": "code_review",
        "tester_agent": "testing",
        "security_agent": "security",
        "devops_agent": "devops",
    }

    if state.current_agent and state.current_agent in agent_mapping:
        logger.info(f"Routing to agent: {state.current_agent}")
        return agent_mapping[state.current_agent]

    # Check if workflow is explicitly complete
    if state.workflow_complete:
        logger.info("Workflow marked as complete")
        return END
    
    # Check if we've exceeded max iterations (safety limit)
    if state.iteration_count >= 50:
        logger.warning("Max iterations reached, ending workflow")
        return END

    # Check phase-based completion
    if state.phase == AgentPhase.MONITORING and not state.task_queue:
        logger.info("Workflow complete - monitoring phase with no tasks")
        return END

    # Default: end (orchestrator should explicitly delegate)
    logger.info("No delegation, ending workflow")
    return END


def route_from_agent(
    state: SDLCState,
) -> Literal["orchestrator", "human_input", "__end__"]:
    """Route from any agent back to orchestrator or human input."""
    if state.awaiting_human_input:
        return "human_input"

    # Return to orchestrator for next decision
    # Note: Don't mutate state here - nodes should clear current_agent
    return "orchestrator"


def route_from_human_input(state: SDLCState) -> Literal["orchestrator"]:
    """Route from human input back to orchestrator."""
    # Reset human input state
    state.awaiting_human_input = False
    return "orchestrator"


# =============================================================================
# Graph Builder
# =============================================================================


def create_sdlc_graph() -> StateGraph:
    """
    Create the SDLC agent graph.

    Returns:
        Configured StateGraph
    """
    # Create graph with unified state
    graph = StateGraph(SDLCState)

    # Add nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("requirements", requirements_node)
    graph.add_node("planning", planning_node)
    graph.add_node("developer", developer_node)
    graph.add_node("code_review", code_review_node)
    graph.add_node("testing", testing_node)
    graph.add_node("security", security_node)
    graph.add_node("devops", devops_node)
    graph.add_node("human_input", human_input_node)

    # Set entry point
    graph.set_entry_point("orchestrator")

    # Add conditional edges from orchestrator
    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "requirements": "requirements",
            "planning": "planning",
            "developer": "developer",
            "code_review": "code_review",
            "testing": "testing",
            "security": "security",
            "devops": "devops",
            "human_input": "human_input",
            END: END,
        },
    )

    # Add edges from agents back to orchestrator
    for agent_node in [
        "requirements",
        "planning",
        "developer",
        "code_review",
        "testing",
        "security",
        "devops",
    ]:
        graph.add_conditional_edges(
            agent_node,
            route_from_agent,
            {
                "orchestrator": "orchestrator",
                "human_input": "human_input",
                END: END,
            },
        )

    # Add edge from human input back to orchestrator
    graph.add_edge("human_input", "orchestrator")

    return graph


def compile_sdlc_graph(checkpointer: Any = None):
    """
    Compile the SDLC graph with optional checkpointer.

    Args:
        checkpointer: LangGraph checkpointer for persistence

    Returns:
        Compiled graph
    """
    graph = create_sdlc_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_input"],  # Interrupt before human input
    )


# =============================================================================
# Graph Executor
# =============================================================================


async def run_sdlc_workflow(
    project_id: str,
    workflow_id: str,
    objective: str,
    config: dict[str, Any] | None = None,
) -> SDLCState:
    """
    Run the SDLC workflow for a project.

    Args:
        project_id: Project identifier
        workflow_id: Workflow identifier
        objective: Project objective/requirements
        config: Optional configuration

    Returns:
        Final workflow state
    """
    # Create initial state
    initial_state = SDLCState(
        workflow_id=workflow_id,
        project_id=project_id,
        phase=AgentPhase.REQUIREMENTS,
        objective=objective,
        metadata=config or {},
    )

    # Compile graph
    graph = compile_sdlc_graph()

    # Run the graph
    thread_config = {"configurable": {"thread_id": workflow_id}}

    logger.info(
        "Starting SDLC workflow",
        project_id=project_id,
        workflow_id=workflow_id,
    )

    async for event in graph.astream(initial_state, thread_config):
        logger.debug("Graph event", event=event)

    # Get final state
    final_state = graph.get_state(thread_config)

    logger.info(
        "SDLC workflow completed",
        workflow_id=workflow_id,
        phase=final_state.values.get("phase") if final_state.values else None,
    )

    return final_state.values if final_state.values else initial_state
