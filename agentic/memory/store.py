"""Memory store for state persistence."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog

from agentic.config import settings
from agentic.state.schemas import SDLCState


logger = structlog.get_logger()


class MemoryStore(ABC):
    """Abstract base class for memory storage."""

    @abstractmethod
    async def save_state(self, state: SDLCState) -> None:
        """Save the current state."""
        pass

    @abstractmethod
    async def load_state(self, project_id: UUID) -> SDLCState | None:
        """Load state by project ID."""
        pass

    @abstractmethod
    async def list_projects(self) -> list[dict[str, Any]]:
        """List all saved projects."""
        pass

    @abstractmethod
    async def delete_state(self, project_id: UUID) -> bool:
        """Delete a saved state."""
        pass


class LocalMemoryStore(MemoryStore):
    """Local file-based memory store."""

    def __init__(self, base_path: Path | None = None):
        """Initialize the local memory store."""
        self.base_path = base_path or settings.checkpoint_dir
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(store="local")

    def _get_state_path(self, project_id: UUID) -> Path:
        """Get the path for a state file."""
        return self.base_path / f"{project_id}.json"

    def _serialize_state(self, state: SDLCState) -> str:
        """Serialize state to JSON."""
        return state.model_dump_json(indent=2)

    def _deserialize_state(self, data: str) -> SDLCState:
        """Deserialize state from JSON."""
        return SDLCState.model_validate_json(data)

    async def save_state(self, state: SDLCState) -> None:
        """Save state to a local file."""
        path = self._get_state_path(state.project_id)
        
        try:
            path.write_text(self._serialize_state(state))
            self.logger.info(
                "State saved",
                project_id=str(state.project_id),
                phase=state.current_phase.value,
            )
        except Exception as e:
            self.logger.error("Failed to save state", error=str(e))
            raise

    async def load_state(self, project_id: UUID) -> SDLCState | None:
        """Load state from a local file."""
        path = self._get_state_path(project_id)
        
        if not path.exists():
            self.logger.warning("State not found", project_id=str(project_id))
            return None
        
        try:
            data = path.read_text()
            state = self._deserialize_state(data)
            self.logger.info(
                "State loaded",
                project_id=str(project_id),
                phase=state.current_phase.value,
            )
            return state
        except Exception as e:
            self.logger.error("Failed to load state", error=str(e))
            raise

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all saved projects."""
        projects = []
        
        for path in self.base_path.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                projects.append({
                    "project_id": data.get("project_id"),
                    "project_name": data.get("project_name", "Unknown"),
                    "current_phase": data.get("current_phase"),
                    "started_at": data.get("started_at"),
                    "updated_at": data.get("updated_at"),
                })
            except Exception:
                continue
        
        return sorted(projects, key=lambda x: x.get("updated_at", ""), reverse=True)

    async def delete_state(self, project_id: UUID) -> bool:
        """Delete a saved state."""
        path = self._get_state_path(project_id)
        
        if path.exists():
            path.unlink()
            self.logger.info("State deleted", project_id=str(project_id))
            return True
        
        return False


class CheckpointManager:
    """Manager for automatic checkpointing during pipeline execution."""

    def __init__(self, store: MemoryStore | None = None):
        """Initialize the checkpoint manager."""
        self.store = store or LocalMemoryStore()
        self.logger = logger.bind(component="checkpoint")

    async def checkpoint(self, state: SDLCState, phase: str) -> None:
        """Create a checkpoint at the current phase."""
        state.updated_at = datetime.now()
        await self.store.save_state(state)
        self.logger.info("Checkpoint created", phase=phase)

    async def restore(self, project_id: UUID) -> SDLCState | None:
        """Restore from the latest checkpoint."""
        state = await self.store.load_state(project_id)
        if state:
            self.logger.info(
                "Restored from checkpoint",
                project_id=str(project_id),
                phase=state.current_phase.value,
            )
        return state

    async def get_project_history(self, project_id: UUID) -> list[dict[str, Any]]:
        """Get the phase history for a project."""
        state = await self.store.load_state(project_id)
        if not state:
            return []
        
        return [
            {"phase": phase.value, "index": i}
            for i, phase in enumerate(state.phase_history)
        ]
