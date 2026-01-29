# =============================================================================
# SDLC Agent - Workflow Execution Service
# =============================================================================
# Service for executing workflows and recording agent activity to the database.
# =============================================================================

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.agents import SDLCState, compile_sdlc_graph
from sdlc_agent.agents.base import AgentPhase
from sdlc_agent.api.websocket import (
    emit_agent_completed,
    emit_agent_failed,
    emit_agent_progress,
    emit_agent_started,
    emit_workflow_status,
)
from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import (
    AgentExecution,
    Workflow,
    WorkflowStatus,
    get_session_context,
)

logger = get_logger(__name__)
settings = get_settings()


async def enqueue_workflow(
    workflow_id: str,
    project_id: str,
    objective: str,
    config: dict[str, Any] | None = None,
) -> None:
    """
    Enqueue a workflow for background execution.
    
    Args:
        workflow_id: Workflow UUID
        project_id: Project UUID
        objective: Project objective/requirements
        config: Optional configuration
    """
    redis_client = redis.from_url(str(settings.redis.url))
    
    task = {
        "id": workflow_id,
        "type": "run_workflow",
        "workflow_id": workflow_id,
        "project_id": project_id,
        "objective": objective,
        "config": config or {},
        "queued_at": datetime.now(UTC).isoformat(),
    }
    
    await redis_client.lpush("sdlc:tasks", json.dumps(task))
    await redis_client.aclose()
    
    logger.info(
        "Workflow enqueued",
        workflow_id=workflow_id,
        project_id=project_id,
    )


async def execute_workflow(
    workflow_id: str,
    project_id: str,
    objective: str,
    config: dict[str, Any] | None = None,
) -> SDLCState:
    """
    Execute a workflow and record agent executions to the database.
    
    Args:
        workflow_id: Workflow UUID
        project_id: Project UUID
        objective: Project objective
        config: Optional configuration
        
    Returns:
        Final workflow state
    """
    logger.info(
        "Starting workflow execution",
        workflow_id=workflow_id,
        project_id=project_id,
    )
    
    # Update workflow status to running
    async with get_session_context() as session:
        workflow = await session.get(Workflow, workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(UTC)
            await session.commit()
    
    # Create initial state
    initial_state = SDLCState(
        workflow_id=workflow_id,
        project_id=project_id,
        phase=AgentPhase.REQUIREMENTS,
        objective=objective,
        metadata={
            **(config or {}),
            "project_id": project_id,  # Ensure project_id is in metadata for agents
        },
    )
    
    # Compile graph
    graph = compile_sdlc_graph()
    thread_config = {"configurable": {"thread_id": workflow_id}}
    
    current_agent: str | None = None
    execution_id: str | None = None
    execution_start: datetime | None = None
    
    try:
        async for event in graph.astream(initial_state, thread_config):
            # Track agent transitions and record executions
            for node_name, node_output in event.items():
                if node_name != current_agent:
                    # Finish previous execution
                    if current_agent and execution_id:
                        duration = (datetime.now(UTC) - execution_start).total_seconds() if execution_start else 0
                        tokens = node_output.tokens_used if hasattr(node_output, 'tokens_used') else 0
                        
                        await _finish_execution(
                            execution_id=execution_id,
                            success=True,
                            output_data={"phase": node_output.phase.value if hasattr(node_output, 'phase') else None},
                            tokens_used=tokens,
                        )
                        
                        # Emit WebSocket event for agent completion
                        try:
                            await emit_agent_completed(
                                workflow_id=workflow_id,
                                agent_type=current_agent,
                                action="completed",
                                details=f"{_get_agent_name(current_agent)} finished processing",
                                duration=duration,
                                tokens_used=tokens,
                            )
                        except Exception:
                            pass  # Don't fail workflow if WebSocket emit fails
                    
                    # Start new execution
                    if node_name not in ("__end__",):
                        current_agent = node_name
                        execution_start = datetime.now(UTC)
                        execution_id = await _start_execution(
                            workflow_id=workflow_id,
                            agent_type=node_name,
                            agent_name=_get_agent_name(node_name),
                        )
                        
                        logger.info(
                            "Agent started",
                            workflow_id=workflow_id,
                            agent=node_name,
                            execution_id=execution_id,
                        )
                        
                        # Emit WebSocket event for agent start
                        try:
                            await emit_agent_started(
                                workflow_id=workflow_id,
                                agent_type=node_name,
                                action="started",
                                details=f"{_get_agent_name(node_name)} is processing",
                            )
                            
                            # Emit workflow status update
                            phase = node_output.phase.value if hasattr(node_output, 'phase') else "unknown"
                            await emit_workflow_status(
                                workflow_id=workflow_id,
                                status="running",
                                phase=phase,
                            )
                        except Exception:
                            pass  # Don't fail workflow if WebSocket emit fails
        
        # Finish last execution
        if current_agent and execution_id:
            duration = (datetime.now(UTC) - execution_start).total_seconds() if execution_start else 0
            
            await _finish_execution(
                execution_id=execution_id,
                success=True,
                output_data={},
                tokens_used=0,
            )
            
            # Emit completion event
            try:
                await emit_agent_completed(
                    workflow_id=workflow_id,
                    agent_type=current_agent,
                    action="completed",
                    details=f"{_get_agent_name(current_agent)} finished processing",
                    duration=duration,
                )
            except Exception:
                pass
        
        # Get final state
        final_state = graph.get_state(thread_config)
        state_values = final_state.values if final_state.values else {}
        
        # Handle both dict and SDLCState
        if isinstance(state_values, dict):
            awaiting_input = state_values.get("awaiting_human_input", False)
            phase_value = state_values.get("phase", AgentPhase.REQUIREMENTS)
            if hasattr(phase_value, "value"):
                phase_value = phase_value.value
            iteration_count = state_values.get("iteration_count", 0)
            tokens = state_values.get("tokens_used", 0)
        else:
            awaiting_input = state_values.awaiting_human_input
            phase_value = state_values.phase.value
            iteration_count = state_values.iteration_count
            tokens = state_values.tokens_used
        
        # Update workflow status
        async with get_session_context() as session:
            workflow = await session.get(Workflow, workflow_id)
            if workflow:
                if awaiting_input:
                    workflow.status = WorkflowStatus.AWAITING_INPUT
                else:
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now(UTC)
                
                workflow.current_state = {
                    "phase": phase_value,
                    "iteration_count": iteration_count,
                    "tokens_used": tokens,
                }
                await session.commit()
        
        # Emit final workflow status
        try:
            status = "awaiting_input" if awaiting_input else "completed"
            await emit_workflow_status(
                workflow_id=workflow_id,
                status=status,
                phase=phase_value,
            )
        except Exception:
            pass
        
        logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            phase=phase_value,
        )
        
        return state_values
        
    except Exception as e:
        logger.exception("Workflow execution failed", error=str(e))
        
        # Finish failed execution
        if execution_id:
            await _finish_execution(
                execution_id=execution_id,
                success=False,
                error_message=str(e),
            )
            
            # Emit failure event
            try:
                await emit_agent_failed(
                    workflow_id=workflow_id,
                    agent_type=current_agent or "unknown",
                    action="failed",
                    details="Workflow execution failed",
                    error=str(e),
                )
            except Exception:
                pass
        
        # Update workflow status
        async with get_session_context() as session:
            workflow = await session.get(Workflow, workflow_id)
            if workflow:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = str(e)
                workflow.completed_at = datetime.now(UTC)
                await session.commit()
        
        # Emit workflow failed status
        try:
            await emit_workflow_status(
                workflow_id=workflow_id,
                status="failed",
                phase="error",
            )
        except Exception:
            pass
        
        raise


async def _start_execution(
    workflow_id: str,
    agent_type: str,
    agent_name: str,
) -> str:
    """Start a new agent execution record."""
    async with get_session_context() as session:
        execution = AgentExecution(
            workflow_id=workflow_id,
            agent_type=agent_type,
            agent_name=agent_name,
            started_at=datetime.now(UTC),
            input_data={},
            tokens_used=0,
            iterations=0,
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return str(execution.id)


async def _finish_execution(
    execution_id: str,
    success: bool,
    output_data: dict[str, Any] | None = None,
    tokens_used: int = 0,
    error_message: str | None = None,
) -> None:
    """Finish an agent execution record."""
    async with get_session_context() as session:
        execution = await session.get(AgentExecution, execution_id)
        if execution:
            execution.completed_at = datetime.now(UTC)
            execution.success = success
            execution.output_data = output_data or {}
            execution.tokens_used = tokens_used
            execution.error_message = error_message
            await session.commit()


def _get_agent_name(node_name: str) -> str:
    """Get human-readable agent name."""
    names = {
        "orchestrator": "Orchestrator Agent",
        "requirements": "Requirements Agent",
        "planning": "Planning Agent",
        "developer": "Developer Agent",
        "code_review": "Code Review Agent",
        "testing": "Testing Agent",
        "security": "Security Agent",
        "devops": "DevOps Agent",
        "human_input": "Awaiting Human Input",
    }
    return names.get(node_name, node_name.replace("_", " ").title())
