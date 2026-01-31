# =============================================================================
# SDLC Agent - Artifact Persistence Service
# =============================================================================
"""
Service for persisting artifacts to the database.
Handles requirements documents, code, tests, and other generated artifacts.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import Artifact, get_session_context

logger = get_logger(__name__)


class ArtifactService:
    """Service for managing artifacts in the database."""

    @staticmethod
    async def create_artifact(
        name: str,
        artifact_type: str,
        content: str | None = None,
        workflow_id: uuid.UUID | None = None,
        task_id: uuid.UUID | None = None,
        file_path: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Artifact:
        """
        Create an artifact in the database.

        Args:
            name: Artifact name/title
            artifact_type: Type of artifact (requirements, code, test, doc, etc.)
            content: Text content of the artifact
            workflow_id: Optional workflow this artifact belongs to
            task_id: Optional task this artifact belongs to
            file_path: Optional file path for code artifacts
            extra_data: Additional metadata

        Returns:
            Created Artifact
        """
        content_hash = None
        if content:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

        async with get_session_context() as session:
            artifact = Artifact(
                name=name,
                artifact_type=artifact_type,
                content=content,
                content_hash=content_hash,
                workflow_id=workflow_id,
                task_id=task_id,
                file_path=file_path,
                extra_data=extra_data or {},
            )
            session.add(artifact)
            await session.flush()
            await session.refresh(artifact)

            logger.info(
                "Artifact created",
                artifact_id=str(artifact.id),
                name=name,
                artifact_type=artifact_type,
                workflow_id=str(workflow_id) if workflow_id else None,
            )
            return artifact

    @staticmethod
    async def create_requirements_traceability(
        workflow_id: uuid.UUID,
        original_requirements: str,
        human_inputs: list[dict[str, Any]],
        functional_requirements: list[dict[str, Any]],
        non_functional_requirements: list[dict[str, Any]],
        epics: list[dict[str, Any]],
        user_stories: list[dict[str, Any]],
    ) -> Artifact:
        """
        Create a comprehensive requirements traceability artifact.

        This captures the complete journey from original requirements through
        human input clarifications to generated epics and stories.

        Args:
            workflow_id: The workflow this belongs to
            original_requirements: The initial requirements/objective
            human_inputs: List of human input requests and responses
            functional_requirements: Generated functional requirements
            non_functional_requirements: Generated non-functional requirements
            epics: Generated epics
            user_stories: Generated user stories

        Returns:
            Created requirements traceability Artifact
        """
        # Build traceability document
        traceability = {
            "original_requirements": original_requirements,
            "human_inputs": [
                {
                    "type": hi.get("type", "clarification"),
                    "question": hi.get("question") or hi.get("prompt", ""),
                    "context": hi.get("context", ""),
                    "options": hi.get("options", []),
                    "response": hi.get("response", {}),
                    "timestamp": hi.get("timestamp") or hi.get("requested_at", ""),
                }
                for hi in human_inputs
            ],
            "requirements": {
                "functional": functional_requirements,
                "non_functional": non_functional_requirements,
            },
            "epics": [
                {
                    "id": epic.get("id"),
                    "db_id": epic.get("db_id"),
                    "title": epic.get("title"),
                    "description": epic.get("description"),
                    "business_value": epic.get("business_value"),
                    "requirement_ids": epic.get("requirement_ids", []),  # Link to requirements
                    "story_count": len(epic.get("stories", [])),
                }
                for epic in epics
            ],
            "user_stories": [
                {
                    "id": story.get("id"),
                    "db_id": story.get("db_id"),
                    "epic_id": story.get("epic_id"),
                    "title": story.get("title"),
                    "user_story": story.get("user_story"),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "requirement_ids": story.get("requirement_ids", []),  # Link to requirements
                }
                for story in user_stories
            ],
            "summary": {
                "total_functional_requirements": len(functional_requirements),
                "total_non_functional_requirements": len(non_functional_requirements),
                "total_epics": len(epics),
                "total_stories": len(user_stories),
                "total_human_inputs": len(human_inputs),
            },
        }

        content = json.dumps(traceability, indent=2)

        return await ArtifactService.create_artifact(
            name="Requirements Traceability Document",
            artifact_type="requirements",
            content=content,
            workflow_id=workflow_id,
            extra_data={
                "summary": traceability["summary"],
                "has_human_inputs": len(human_inputs) > 0,
            },
        )

    @staticmethod
    async def get_workflow_artifacts(
        workflow_id: uuid.UUID,
        artifact_type: str | None = None,
    ) -> list[Artifact]:
        """
        Get all artifacts for a workflow.

        Args:
            workflow_id: Workflow UUID
            artifact_type: Optional filter by type

        Returns:
            List of artifacts
        """
        from sqlalchemy import select

        async with get_session_context() as session:
            query = select(Artifact).where(Artifact.workflow_id == workflow_id)
            if artifact_type:
                query = query.where(Artifact.artifact_type == artifact_type)
            query = query.order_by(Artifact.created_at.desc())

            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_artifact(artifact_id: uuid.UUID) -> Artifact | None:
        """
        Get an artifact by ID.

        Args:
            artifact_id: Artifact UUID

        Returns:
            Artifact or None
        """
        async with get_session_context() as session:
            return await session.get(Artifact, artifact_id)
