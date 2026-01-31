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

from sdlc_agent.agents import SDLCState, compile_sdlc_graph_async
from sdlc_agent.agents.base import AgentPhase
from sdlc_agent.api.routes.settings import get_max_iterations
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
    HumanInput,
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
        config: Optional configuration (may include resume_from_input=True)
        
    Returns:
        Final workflow state
    """
    is_resume = config.get("resume_from_input", False) if config else False
    human_response = config.get("human_input_response") if config else None
    
    logger.info(
        "Starting workflow execution",
        workflow_id=workflow_id,
        project_id=project_id,
        is_resume=is_resume,
    )
    
    # Update workflow status to running
    async with get_session_context() as session:
        workflow = await session.get(Workflow, workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.RUNNING
            if not is_resume:
                workflow.started_at = datetime.now(UTC)
            await session.commit()
    
    # Compile graph with async checkpointer
    graph = await compile_sdlc_graph_async()
    thread_config = {"configurable": {"thread_id": workflow_id}}
    
    # Load max_iterations from settings
    max_iterations = await get_max_iterations()
    
    # For resumption, we get existing state and update with human response
    # For new workflows, we create initial state
    if is_resume:
        # Get existing state from checkpoint (use async method for AsyncPostgresSaver)
        existing_state = await graph.aget_state(thread_config)
        if existing_state and existing_state.values:
            state_values = existing_state.values
            # Update state with human response
            if isinstance(state_values, dict):
                state_values["awaiting_human_input"] = False
                state_values["human_input_response"] = human_response
                state_values["human_input_request"] = None
            else:
                state_values.awaiting_human_input = False
                state_values.human_input_response = human_response
                state_values.human_input_request = None
            
            # Update state in checkpoint (use async method)
            await graph.aupdate_state(thread_config, state_values)
            input_state = None  # Resume with no new input
            logger.info("Resuming workflow from checkpoint", workflow_id=workflow_id)
        else:
            # No checkpoint found - create fresh state with human response included
            logger.warning("No checkpoint found for resume, starting fresh with human response", workflow_id=workflow_id)
            
            # Build enhanced objective with human response
            enhanced_objective = objective
            if human_response:
                response_str = json.dumps(human_response) if isinstance(human_response, dict) else str(human_response)
                enhanced_objective = f"{objective}\n\nUser clarification: {response_str}"
            
            input_state = SDLCState(
                workflow_id=workflow_id,
                project_id=project_id,
                phase=AgentPhase.REQUIREMENTS,
                objective=enhanced_objective,
                human_input_response=human_response,
                max_iterations=max_iterations,
                metadata={**(config or {}), "project_id": project_id},
            )
    else:
        # Create initial state for new workflows
        input_state = SDLCState(
            workflow_id=workflow_id,
            project_id=project_id,
            phase=AgentPhase.REQUIREMENTS,
            objective=objective,
            max_iterations=max_iterations,
            metadata={
                **(config or {}),
                "project_id": project_id,  # Ensure project_id is in metadata for agents
            },
        )
    
    current_agent: str | None = None
    execution_id: str | None = None
    execution_start: datetime | None = None
    previous_tokens: int = 0  # Track previous token count to calculate delta
    
    try:
        async for event in graph.astream(input_state, thread_config):
            # Track agent transitions and record executions
            for node_name, node_output in event.items():
                # Skip internal LangGraph nodes (not real agents)
                if node_name.startswith("__"):
                    continue
                
                # Extract current total tokens and iterations from state
                current_tokens = 0
                current_iterations = 0
                if hasattr(node_output, 'tokens_used'):
                    current_tokens = node_output.tokens_used or 0
                elif isinstance(node_output, dict):
                    current_tokens = node_output.get('tokens_used', 0) or 0
                if hasattr(node_output, 'iteration_count'):
                    current_iterations = node_output.iteration_count or 0
                elif isinstance(node_output, dict):
                    current_iterations = node_output.get('iteration_count', 0) or 0
                    
                if node_name != current_agent:
                    # Finish previous execution with token delta
                    if current_agent and execution_id:
                        duration = (datetime.now(UTC) - execution_start).total_seconds() if execution_start else 0
                        # Calculate tokens used by this agent (delta from previous)
                        agent_tokens = max(0, current_tokens - previous_tokens)
                        previous_tokens = current_tokens  # Update for next agent
                        
                        await _finish_execution(
                            execution_id=execution_id,
                            success=True,
                            output_data={
                                "phase": node_output.phase.value if hasattr(node_output, 'phase') else None,
                                "iteration_count": current_iterations,
                            },
                            tokens_used=agent_tokens,
                            iterations=current_iterations,
                        )
                        
                        # Emit WebSocket event for agent completion
                        try:
                            await emit_agent_completed(
                                workflow_id=workflow_id,
                                agent_type=current_agent,
                                action="completed",
                                details=f"{_get_agent_name(current_agent)} finished processing",
                                duration=duration,
                                tokens_used=agent_tokens,
                            )
                        except Exception:
                            pass  # Don't fail workflow if WebSocket emit fails
                    
                    # Start new execution (skip internal nodes)
                    if not node_name.startswith("__"):
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
                            iteration_count = node_output.iteration_count if hasattr(node_output, 'iteration_count') else 0
                            tokens = node_output.tokens_used if hasattr(node_output, 'tokens_used') else 0
                            await emit_workflow_status(
                                workflow_id=workflow_id,
                                status="running",
                                phase=phase,
                            )
                            
                            # Update workflow.current_state in database for real-time visibility
                            async with get_session_context() as session:
                                workflow = await session.get(Workflow, workflow_id)
                                if workflow:
                                    workflow.current_state = {
                                        "phase": phase,
                                        "iteration_count": iteration_count,
                                        "tokens_used": tokens,
                                    }
                                    await session.commit()
                        except Exception:
                            pass  # Don't fail workflow if WebSocket/DB update fails
        
        # Get final state to extract final token count
        final_state = await graph.aget_state(thread_config)
        state_values = final_state.values if final_state.values else {}
        
        # Extract final totals
        final_tokens = 0
        final_iterations = 0
        if isinstance(state_values, dict):
            final_tokens = state_values.get("tokens_used", 0) or 0
            final_iterations = state_values.get("iteration_count", 0) or 0
        else:
            final_tokens = getattr(state_values, 'tokens_used', 0) or 0
            final_iterations = getattr(state_values, 'iteration_count', 0) or 0
        
        # Finish last execution with remaining tokens
        if current_agent and execution_id:
            duration = (datetime.now(UTC) - execution_start).total_seconds() if execution_start else 0
            last_agent_tokens = max(0, final_tokens - previous_tokens)
            
            await _finish_execution(
                execution_id=execution_id,
                success=True,
                output_data={"iteration_count": final_iterations},
                tokens_used=last_agent_tokens,
                iterations=final_iterations,
            )
            
            # Emit completion event
            try:
                await emit_agent_completed(
                    workflow_id=workflow_id,
                    agent_type=current_agent,
                    action="completed",
                    details=f"{_get_agent_name(current_agent)} finished processing",
                    duration=duration,
                    tokens_used=last_agent_tokens,
                )
            except Exception:
                pass
        
        # Handle both dict and SDLCState for human input detection
        if isinstance(state_values, dict):
            awaiting_input = state_values.get("awaiting_human_input", False)
            human_input_request = state_values.get("human_input_request", {})
            phase_value = state_values.get("phase", AgentPhase.REQUIREMENTS)
            if hasattr(phase_value, "value"):
                phase_value = phase_value.value
            elif isinstance(phase_value, str):
                phase_value = phase_value  # Already a string
            iteration_count = final_iterations
            tokens = final_tokens
        else:
            awaiting_input = state_values.awaiting_human_input
            human_input_request = state_values.human_input_request or {}
            # Handle phase being either an enum or a string
            if hasattr(state_values.phase, "value"):
                phase_value = state_values.phase.value
            else:
                phase_value = state_values.phase  # Already a string
            iteration_count = final_iterations
            tokens = final_tokens
        
        # Update workflow status and create human input record if needed
        async with get_session_context() as session:
            workflow = await session.get(Workflow, workflow_id)
            if workflow:
                if awaiting_input:
                    workflow.status = WorkflowStatus.AWAITING_INPUT
                    
                    # Create human input record in database
                    if human_input_request:
                        human_input = HumanInput(
                            workflow_id=workflow_id,
                            request_type=human_input_request.get("type", "clarification"),
                            prompt=human_input_request.get("question", ""),
                            context={
                                "original_context": human_input_request.get("context", ""),
                                "options": human_input_request.get("options", []),
                                "phase": phase_value,
                            },
                            is_resolved=False,
                        )
                        session.add(human_input)
                        logger.info(
                            "Created human input request",
                            workflow_id=workflow_id,
                            request_type=human_input.request_type,
                        )
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
    iterations: int = 0,
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
            execution.iterations = iterations
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
