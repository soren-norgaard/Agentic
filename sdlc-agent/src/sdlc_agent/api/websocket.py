# =============================================================================
# SDLC Agent - WebSocket Handler
# =============================================================================
# Socket.IO based real-time communication for agent activity updates.
# =============================================================================

from __future__ import annotations

from typing import Any

import socketio
from socketio import AsyncServer

from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)

# Create Socket.IO server
sio = AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Track subscriptions
_workflow_subscribers: dict[str, set[str]] = {}  # workflow_id -> set of session ids
_project_subscribers: dict[str, set[str]] = {}   # project_id -> set of session ids


# =============================================================================
# Connection Events
# =============================================================================


@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None) -> bool:
    """Handle new client connections."""
    logger.info("Client connected", session_id=sid)
    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnections."""
    logger.info("Client disconnected", session_id=sid)
    
    # Clean up subscriptions
    for workflow_id, subscribers in list(_workflow_subscribers.items()):
        subscribers.discard(sid)
        if not subscribers:
            del _workflow_subscribers[workflow_id]
    
    for project_id, subscribers in list(_project_subscribers.items()):
        subscribers.discard(sid)
        if not subscribers:
            del _project_subscribers[project_id]


# =============================================================================
# Subscription Events
# =============================================================================


@sio.on("subscribe:workflow")
async def subscribe_workflow(sid: str, workflow_id: str) -> None:
    """Subscribe to workflow updates."""
    logger.debug("Client subscribing to workflow", session_id=sid, workflow_id=workflow_id)
    
    if workflow_id not in _workflow_subscribers:
        _workflow_subscribers[workflow_id] = set()
    _workflow_subscribers[workflow_id].add(sid)
    
    # Join a room for easier broadcasting
    await sio.enter_room(sid, f"workflow:{workflow_id}")


@sio.on("unsubscribe:workflow")
async def unsubscribe_workflow(sid: str, workflow_id: str) -> None:
    """Unsubscribe from workflow updates."""
    logger.debug("Client unsubscribing from workflow", session_id=sid, workflow_id=workflow_id)
    
    if workflow_id in _workflow_subscribers:
        _workflow_subscribers[workflow_id].discard(sid)
        if not _workflow_subscribers[workflow_id]:
            del _workflow_subscribers[workflow_id]
    
    await sio.leave_room(sid, f"workflow:{workflow_id}")


@sio.on("subscribe:project")
async def subscribe_project(sid: str, project_id: str) -> None:
    """Subscribe to project updates."""
    logger.debug("Client subscribing to project", session_id=sid, project_id=project_id)
    
    if project_id not in _project_subscribers:
        _project_subscribers[project_id] = set()
    _project_subscribers[project_id].add(sid)
    
    await sio.enter_room(sid, f"project:{project_id}")


@sio.on("unsubscribe:project")
async def unsubscribe_project(sid: str, project_id: str) -> None:
    """Unsubscribe from project updates."""
    logger.debug("Client unsubscribing from project", session_id=sid, project_id=project_id)
    
    if project_id in _project_subscribers:
        _project_subscribers[project_id].discard(sid)
        if not _project_subscribers[project_id]:
            del _project_subscribers[project_id]
    
    await sio.leave_room(sid, f"project:{project_id}")


# =============================================================================
# Emit Functions (called from other parts of the application)
# =============================================================================


async def emit_agent_started(
    workflow_id: str,
    agent_type: str,
    action: str,
    details: str,
) -> None:
    """Emit agent started event."""
    await sio.emit(
        "agent:started",
        {
            "workflowId": workflow_id,
            "agentType": agent_type,
            "action": action,
            "details": details,
        },
        room=f"workflow:{workflow_id}",
    )


async def emit_agent_progress(
    workflow_id: str,
    agent_type: str,
    action: str,
    details: str,
    tokens_used: int | None = None,
) -> None:
    """Emit agent progress event."""
    data = {
        "workflowId": workflow_id,
        "agentType": agent_type,
        "action": action,
        "details": details,
    }
    if tokens_used is not None:
        data["tokensUsed"] = tokens_used
    
    await sio.emit(
        "agent:progress",
        data,
        room=f"workflow:{workflow_id}",
    )


async def emit_agent_completed(
    workflow_id: str,
    agent_type: str,
    action: str,
    details: str,
    duration: float | None = None,
    tokens_used: int | None = None,
) -> None:
    """Emit agent completed event."""
    data = {
        "workflowId": workflow_id,
        "agentType": agent_type,
        "action": action,
        "details": details,
    }
    if duration is not None:
        data["duration"] = duration
    if tokens_used is not None:
        data["tokensUsed"] = tokens_used
    
    await sio.emit(
        "agent:completed",
        data,
        room=f"workflow:{workflow_id}",
    )


async def emit_agent_failed(
    workflow_id: str,
    agent_type: str,
    action: str,
    details: str,
    error: str | None = None,
) -> None:
    """Emit agent failed event."""
    data = {
        "workflowId": workflow_id,
        "agentType": agent_type,
        "action": action,
        "details": details,
    }
    if error:
        data["error"] = error
    
    await sio.emit(
        "agent:failed",
        data,
        room=f"workflow:{workflow_id}",
    )


async def emit_workflow_status(
    workflow_id: str,
    status: str,
    phase: str,
    completed_tasks: int = 0,
    total_tasks: int = 0,
) -> None:
    """Emit workflow status update."""
    await sio.emit(
        "workflow:status",
        {
            "workflowId": workflow_id,
            "status": status,
            "phase": phase,
            "progress": {
                "completedTasks": completed_tasks,
                "totalTasks": total_tasks,
            },
        },
        room=f"workflow:{workflow_id}",
    )


async def emit_human_input_required(
    workflow_id: str,
    input_id: str,
    agent_type: str,
    prompt: str,
    input_type: str,
    task_id: str | None = None,
    options: list[str] | None = None,
    timeout_at: str | None = None,
) -> None:
    """Emit human input required event."""
    data = {
        "id": input_id,
        "workflowId": workflow_id,
        "agentType": agent_type,
        "prompt": prompt,
        "inputType": input_type,
    }
    if task_id:
        data["taskId"] = task_id
    if options:
        data["options"] = options
    if timeout_at:
        data["timeoutAt"] = timeout_at
    
    await sio.emit(
        "human_input:required",
        data,
        room=f"workflow:{workflow_id}",
    )


async def emit_notification(
    notification_type: str,
    title: str,
    message: str | None = None,
    action_url: str | None = None,
    room: str | None = None,
) -> None:
    """Emit a notification to all connected clients or a specific room."""
    data = {
        "type": notification_type,
        "title": title,
    }
    if message:
        data["message"] = message
    if action_url:
        data["actionUrl"] = action_url
    
    if room:
        await sio.emit("notification", data, room=room)
    else:
        await sio.emit("notification", data)


# =============================================================================
# Socket.IO ASGI App
# =============================================================================


def get_socketio_app():
    """Get the Socket.IO ASGI application."""
    return socketio.ASGIApp(sio, socketio_path="/socket.io")
