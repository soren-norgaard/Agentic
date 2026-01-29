"""SDLC Orchestrator Graph - Main workflow using LangGraph."""

from typing import Any, Literal
from datetime import datetime

import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agentic.agents import (
    ArchitectAgent,
    CodeReviewAgent,
    DeveloperAgent,
    DevOpsAgent,
    IntegrationTestAgent,
    MonitoringAgent,
    PlanningAgent,
    RequirementsAgent,
    SecurityAgent,
    UnitTestAgent,
)
from agentic.agents.base import create_agent_node
from agentic.config import settings
from agentic.state.schemas import Phase, SDLCState, StoryStatus


logger = structlog.get_logger()


# =============================================================================
# State Type for LangGraph (dict-based)
# =============================================================================

# LangGraph works with TypedDict or dict, so we'll use dict and convert


def state_to_dict(state: SDLCState) -> dict[str, Any]:
    """Convert SDLCState to dict for LangGraph."""
    return state.model_dump()


def dict_to_state(data: dict[str, Any]) -> SDLCState:
    """Convert dict back to SDLCState."""
    return SDLCState(**data)


# =============================================================================
# Node Functions
# =============================================================================


async def requirements_node(state: dict) -> dict:
    """Execute requirements analysis."""
    agent = RequirementsAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.PLANNING)
    return state_to_dict(updated)


async def planning_node(state: dict) -> dict:
    """Execute planning and story creation."""
    agent = PlanningAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.ARCHITECTURE)
    return state_to_dict(updated)


async def architecture_node(state: dict) -> dict:
    """Execute architecture design."""
    agent = ArchitectAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.DEVELOPMENT)
    return state_to_dict(updated)


async def development_node(state: dict) -> dict:
    """Execute code development."""
    agent = DeveloperAgent()
    sdlc_state = dict_to_state(state)
    
    # Mark next story as in progress
    for epic in sdlc_state.epics:
        for story in epic.stories:
            if story.status == StoryStatus.REFINED:
                story.status = StoryStatus.IN_PROGRESS
                break
    
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.CODE_REVIEW)
    return state_to_dict(updated)


async def code_review_node(state: dict) -> dict:
    """Execute code review."""
    agent = CodeReviewAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    
    if updated.review_approved:
        updated.transition_to_phase(Phase.TESTING)
    else:
        updated.transition_to_phase(Phase.DEVELOPMENT)  # Back to development
    
    return state_to_dict(updated)


async def testing_node(state: dict) -> dict:
    """Execute testing (unit + integration)."""
    unit_agent = UnitTestAgent()
    integration_agent = IntegrationTestAgent()
    
    sdlc_state = dict_to_state(state)
    
    # Run unit tests
    sdlc_state = await unit_agent.run(sdlc_state)
    
    # Run integration tests
    sdlc_state = await integration_agent.run(sdlc_state)
    
    sdlc_state.transition_to_phase(Phase.SECURITY)
    return state_to_dict(sdlc_state)


async def security_node(state: dict) -> dict:
    """Execute security analysis."""
    agent = SecurityAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    
    if updated.security_approved:
        updated.transition_to_phase(Phase.DEPLOYMENT)
    else:
        # If security issues, go back to development
        updated.transition_to_phase(Phase.DEVELOPMENT)
    
    return state_to_dict(updated)


async def deployment_node(state: dict) -> dict:
    """Execute deployment configuration."""
    agent = DevOpsAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.MONITORING)
    return state_to_dict(updated)


async def monitoring_node(state: dict) -> dict:
    """Execute monitoring setup."""
    agent = MonitoringAgent()
    sdlc_state = dict_to_state(state)
    updated = await agent.run(sdlc_state)
    updated.transition_to_phase(Phase.COMPLETED)
    updated.completed_at = datetime.now()
    return state_to_dict(updated)


# =============================================================================
# Routing Functions
# =============================================================================


def route_after_review(state: dict) -> Literal["testing", "development"]:
    """Route after code review based on approval."""
    if state.get("review_approved", False):
        return "testing"
    return "development"


def route_after_security(state: dict) -> Literal["deployment", "development"]:
    """Route after security based on approval."""
    if state.get("security_approved", False):
        return "deployment"
    return "development"


def should_continue_development(state: dict) -> Literal["code_review", "testing", END]:
    """Check if more stories need development."""
    sdlc_state = dict_to_state(state)
    
    # Check for more stories to develop
    remaining_stories = sdlc_state.get_stories_by_status(StoryStatus.REFINED)
    in_progress = sdlc_state.get_stories_by_status(StoryStatus.IN_PROGRESS)
    in_review = sdlc_state.get_stories_by_status(StoryStatus.IN_REVIEW)
    
    if in_review:
        return "code_review"
    elif remaining_stories or in_progress:
        return "code_review"  # Continue the development cycle
    else:
        return "testing"


def check_iteration_limit(state: dict) -> bool:
    """Check if we've exceeded iteration limits."""
    return state.get("retry_count", 0) < settings.max_retries


# =============================================================================
# Human-in-the-Loop Functions
# =============================================================================


async def human_approval_gate(state: dict, approval_type: str) -> dict:
    """
    Request human approval at key checkpoints.
    
    This is a placeholder - in production, this would integrate with
    a UI, Slack, or other notification system.
    """
    if not settings.require_human_approval:
        return state
    
    sdlc_state = dict_to_state(state)
    
    # Log that approval is needed
    logger.info(
        "Human approval requested",
        approval_type=approval_type,
        phase=sdlc_state.current_phase.value,
    )
    
    # In a real implementation, this would:
    # 1. Send notification to human reviewer
    # 2. Wait for response (with timeout)
    # 3. Record the decision
    
    return state


# =============================================================================
# Graph Construction
# =============================================================================


def create_sdlc_graph() -> StateGraph:
    """
    Create the main SDLC orchestrator graph.
    
    The graph flows through phases:
    Requirements -> Planning -> Architecture -> Development Loop -> 
    Testing -> Security -> Deployment -> Monitoring
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph with dict state
    graph = StateGraph(dict)
    
    # Add nodes for each phase
    graph.add_node("requirements", requirements_node)
    graph.add_node("planning", planning_node)
    graph.add_node("architecture", architecture_node)
    graph.add_node("development", development_node)
    graph.add_node("code_review", code_review_node)
    graph.add_node("testing", testing_node)
    graph.add_node("security", security_node)
    graph.add_node("deployment", deployment_node)
    graph.add_node("monitoring", monitoring_node)
    
    # Define edges (workflow flow)
    graph.add_edge("requirements", "planning")
    graph.add_edge("planning", "architecture")
    graph.add_edge("architecture", "development")
    graph.add_edge("development", "code_review")
    
    # Conditional routing after code review
    graph.add_conditional_edges(
        "code_review",
        route_after_review,
        {
            "testing": "testing",
            "development": "development",
        }
    )
    
    graph.add_edge("testing", "security")
    
    # Conditional routing after security
    graph.add_conditional_edges(
        "security",
        route_after_security,
        {
            "deployment": "deployment",
            "development": "development",
        }
    )
    
    graph.add_edge("deployment", "monitoring")
    graph.add_edge("monitoring", END)
    
    # Set entry point
    graph.set_entry_point("requirements")
    
    return graph


def compile_graph_with_checkpointing():
    """
    Compile the graph with memory checkpointing for persistence.
    
    This allows resuming from checkpoints if the process is interrupted.
    """
    graph = create_sdlc_graph()
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)


# =============================================================================
# Main Execution
# =============================================================================


async def run_sdlc_pipeline(
    project_description: str,
    project_name: str = "New Project",
    config: dict[str, Any] | None = None,
) -> SDLCState:
    """
    Run the full SDLC pipeline for a project.
    
    Args:
        project_description: Natural language description of the project
        project_name: Name for the project
        config: Optional configuration overrides
        
    Returns:
        Final SDLCState with all artifacts
    """
    from agentic.state.schemas import ProjectObjective
    
    logger.info("Starting SDLC pipeline", project_name=project_name)
    
    # Initialize state
    initial_state = SDLCState(
        project_name=project_name,
        objective=ProjectObjective(raw_input=project_description),
        current_phase=Phase.REQUIREMENTS,
    )
    
    # Create and compile graph
    graph = create_sdlc_graph()
    compiled = graph.compile()
    
    # Run the graph
    thread_config = {"configurable": {"thread_id": str(initial_state.project_id)}}
    
    if config:
        thread_config.update(config)
    
    # Execute
    final_state_dict = await compiled.ainvoke(
        state_to_dict(initial_state),
        config=thread_config,
    )
    
    final_state = dict_to_state(final_state_dict)
    
    logger.info(
        "SDLC pipeline completed",
        project_name=project_name,
        final_phase=final_state.current_phase.value,
        epics=len(final_state.epics),
        artifacts=len(final_state.code_artifacts),
        duration=(final_state.completed_at - final_state.started_at).seconds if final_state.completed_at else None,
    )
    
    return final_state


# =============================================================================
# Streaming Execution
# =============================================================================


async def stream_sdlc_pipeline(
    project_description: str,
    project_name: str = "New Project",
):
    """
    Stream the SDLC pipeline execution, yielding state after each phase.
    
    This is useful for real-time progress updates in a UI.
    """
    from agentic.state.schemas import ProjectObjective
    
    logger.info("Starting SDLC pipeline (streaming)", project_name=project_name)
    
    # Initialize state
    initial_state = SDLCState(
        project_name=project_name,
        objective=ProjectObjective(raw_input=project_description),
        current_phase=Phase.REQUIREMENTS,
    )
    
    # Create and compile graph
    graph = create_sdlc_graph()
    compiled = graph.compile()
    
    thread_config = {"configurable": {"thread_id": str(initial_state.project_id)}}
    
    # Stream execution
    async for state_dict in compiled.astream(
        state_to_dict(initial_state),
        config=thread_config,
    ):
        yield dict_to_state(state_dict)
