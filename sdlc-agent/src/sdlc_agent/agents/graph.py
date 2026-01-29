# =============================================================================
# SDLC Agent - Agent Graph (LangGraph)
# =============================================================================
# LangGraph-based workflow that orchestrates all agents.
# =============================================================================

from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from sdlc_agent.agents.base import AgentPhase, AgentState
from sdlc_agent.agents.developer import DeveloperAgent, DeveloperState
from sdlc_agent.agents.orchestrator import OrchestratorAgent, OrchestratorState
from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Graph State (Unified)
# =============================================================================


class SDLCState(OrchestratorState, DeveloperState):
    """
    Unified state that combines all agent-specific states.

    This allows seamless handoffs between agents while maintaining
    all necessary context.
    """

    pass


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
    return await agent.process(state)


async def requirements_node(state: SDLCState) -> SDLCState:
    """Requirements agent node (placeholder)."""
    logger.info("Requirements agent processing")
    # TODO: Implement requirements agent
    return state


async def planning_node(state: SDLCState) -> SDLCState:
    """Planning agent node (placeholder)."""
    logger.info("Planning agent processing")
    # TODO: Implement planning agent
    return state


async def code_review_node(state: SDLCState) -> SDLCState:
    """Code review agent node (placeholder)."""
    logger.info("Code review agent processing")
    # TODO: Implement code review agent
    return state


async def testing_node(state: SDLCState) -> SDLCState:
    """Testing agent node (placeholder)."""
    logger.info("Testing agent processing")
    # TODO: Implement testing agent
    return state


async def security_node(state: SDLCState) -> SDLCState:
    """Security agent node (placeholder)."""
    logger.info("Security agent processing")
    # TODO: Implement security agent
    return state


async def devops_node(state: SDLCState) -> SDLCState:
    """DevOps agent node (placeholder)."""
    logger.info("DevOps agent processing")
    # TODO: Implement devops agent
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
        return agent_mapping[state.current_agent]

    # Check if workflow is complete
    if state.phase == AgentPhase.MONITORING and not state.task_queue:
        return END

    # Default to orchestrator continuing
    return END


def route_from_agent(
    state: SDLCState,
) -> Literal["orchestrator", "human_input", "__end__"]:
    """Route from any agent back to orchestrator or human input."""
    if state.awaiting_human_input:
        return "human_input"

    # Return to orchestrator for next decision
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
