# =============================================================================
# SDLC Agent - Stats/Metrics Routes
# =============================================================================

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import (
    AgentExecution,
    Project,
    ProjectStatus,
    Workflow,
    WorkflowStatus,
    get_session,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class MetricItem(BaseModel):
    """Schema for a single metric."""

    label: str
    value: str
    change: float
    change_label: str


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""

    active_workflows: MetricItem
    tasks_completed: MetricItem
    avg_cycle_time: MetricItem
    tokens_used: MetricItem


# =============================================================================
# Routes
# =============================================================================


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardStats:
    """
    Get dashboard statistics.

    Returns:
        Dashboard metrics overview
    """
    # Count active workflows (running, paused, awaiting_input)
    active_statuses = [
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED,
        WorkflowStatus.AWAITING_INPUT,
    ]
    active_workflow_count = await session.scalar(
        select(func.count(Workflow.id)).where(Workflow.status.in_(active_statuses))
    ) or 0

    # Count total workflows this week (completed)
    completed_count = await session.scalar(
        select(func.count(Workflow.id)).where(Workflow.status == WorkflowStatus.COMPLETED)
    ) or 0

    # Count total agent executions
    total_executions = await session.scalar(
        select(func.count(AgentExecution.id))
    ) or 0

    # Sum tokens used
    total_tokens = await session.scalar(
        select(func.sum(AgentExecution.tokens_used))
    ) or 0

    # Format token count
    if total_tokens >= 1_000_000:
        tokens_display = f"{total_tokens / 1_000_000:.1f}M"
    elif total_tokens >= 1_000:
        tokens_display = f"{total_tokens / 1_000:.1f}K"
    else:
        tokens_display = str(total_tokens)

    return DashboardStats(
        active_workflows=MetricItem(
            label="Active Workflows",
            value=str(active_workflow_count),
            change=0,
            change_label="vs last week",
        ),
        tasks_completed=MetricItem(
            label="Workflows Completed",
            value=str(completed_count),
            change=0,
            change_label="this week",
        ),
        avg_cycle_time=MetricItem(
            label="Agent Executions",
            value=str(total_executions),
            change=0,
            change_label="total",
        ),
        tokens_used=MetricItem(
            label="LLM Tokens Used",
            value=tokens_display,
            change=0,
            change_label="total",
        ),
    )
