# =============================================================================
# SDLC Agent - Worker Process
# =============================================================================
# Background worker that processes agent tasks from the queue.
# =============================================================================

from __future__ import annotations

import asyncio
import signal
from typing import Any

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger, setup_logging
from sdlc_agent.core.telemetry import setup_telemetry
from sdlc_agent.services.workflow_executor import execute_workflow

logger = get_logger(__name__)


class Worker:
    """Background worker for processing agent tasks."""

    def __init__(self) -> None:
        self.running = False
        self.settings = get_settings()

    async def start(self) -> None:
        """Start the worker."""
        self.running = True
        logger.info("Worker starting")

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            await self._process_queue()
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        finally:
            await self._cleanup()

    async def _process_queue(self) -> None:
        """Process tasks from the queue."""
        import redis.asyncio as redis

        redis_client = redis.from_url(str(self.settings.redis.url))

        while self.running:
            try:
                # Block waiting for a task (5 second timeout)
                result = await redis_client.brpop("sdlc:tasks", timeout=5)

                if result:
                    _, task_data = result
                    await self._process_task(task_data)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error processing queue", error=str(e))
                await asyncio.sleep(1)  # Back off on error

        await redis_client.aclose()

    async def _process_task(self, task_data: bytes) -> None:
        """Process a single task."""
        import json

        try:
            task = json.loads(task_data)
            logger.info("Processing task", task_id=task.get("id"))

            task_type = task.get("type")

            if task_type == "run_workflow":
                await self._run_workflow(task)
            elif task_type == "resume_workflow":
                await self._resume_workflow(task)
            else:
                logger.warning("Unknown task type", task_type=task_type)

        except json.JSONDecodeError:
            logger.error("Invalid task data")
        except Exception as e:
            logger.exception("Error processing task", error=str(e))

    async def _run_workflow(self, task: dict[str, Any]) -> None:
        """Run a new workflow."""
        await execute_workflow(
            workflow_id=task.get("workflow_id", ""),
            project_id=task.get("project_id", ""),
            objective=task.get("objective", ""),
            config=task.get("config"),
        )

    async def _resume_workflow(self, task: dict[str, Any]) -> None:
        """Resume a paused workflow with human input."""
        # TODO: Implement workflow resumption
        logger.info("Resuming workflow", workflow_id=task.get("workflow_id"))

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("Shutdown signal received")
        self.running = False

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Worker cleanup complete")


async def main() -> None:
    """Main entry point for the worker."""
    settings = get_settings()
    setup_logging(settings)
    setup_telemetry(settings)

    logger.info("SDLC Agent Worker starting")

    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
