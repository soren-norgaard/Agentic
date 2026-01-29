"""Pydantic schemas for SDLC state management."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class Phase(str, Enum):
    """SDLC phases."""

    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryStatus(str, Enum):
    """Status of a user story."""

    DRAFT = "draft"
    REFINED = "refined"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"


class Severity(str, Enum):
    """Severity levels for findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# =============================================================================
# Core Domain Models
# =============================================================================


class ProjectObjective(BaseModel):
    """High-level project objective from user input."""

    id: UUID = Field(default_factory=uuid4)
    raw_input: str = Field(..., description="Original user input")
    clarified_objective: str | None = Field(
        default=None, description="Clarified and refined objective"
    )
    constraints: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    tech_stack_preferences: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class AcceptanceCriteria(BaseModel):
    """Acceptance criteria for a story."""

    id: UUID = Field(default_factory=uuid4)
    description: str
    is_met: bool = Field(default=False)


class Story(BaseModel):
    """User story with acceptance criteria."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    acceptance_criteria: list[AcceptanceCriteria] = Field(default_factory=list)
    story_points: int | None = Field(default=None, ge=1, le=21)
    status: StoryStatus = Field(default=StoryStatus.DRAFT)
    priority: int = Field(default=0, ge=0, le=100)
    dependencies: list[UUID] = Field(default_factory=list)
    assigned_agent: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Epic(BaseModel):
    """Epic containing multiple related stories."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    stories: list[Story] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.now)


class ArchitectureDecision(BaseModel):
    """Architecture decision record."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    context: str
    decision: str
    rationale: str
    consequences: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class CodeArtifact(BaseModel):
    """Code file artifact."""

    id: UUID = Field(default_factory=uuid4)
    file_path: str
    content: str
    language: str
    story_id: UUID | None = Field(default=None)
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CodeReviewComment(BaseModel):
    """Code review comment."""

    id: UUID = Field(default_factory=uuid4)
    artifact_id: UUID
    line_number: int | None = Field(default=None)
    comment: str
    severity: Severity = Field(default=Severity.INFO)
    is_resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


class TestCase(BaseModel):
    """Test case definition."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    test_type: str  # unit, integration, e2e
    file_path: str | None = Field(default=None)
    story_id: UUID | None = Field(default=None)


class TestResult(BaseModel):
    """Test execution result."""

    id: UUID = Field(default_factory=uuid4)
    test_case_id: UUID | None = Field(default=None)
    test_name: str
    passed: bool
    duration_ms: float | None = Field(default=None)
    error_message: str | None = Field(default=None)
    stack_trace: str | None = Field(default=None)
    coverage_percent: float | None = Field(default=None)
    executed_at: datetime = Field(default_factory=datetime.now)


class SecurityFinding(BaseModel):
    """Security vulnerability finding."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    severity: Severity
    file_path: str | None = Field(default=None)
    line_number: int | None = Field(default=None)
    cwe_id: str | None = Field(default=None)
    remediation: str | None = Field(default=None)
    is_resolved: bool = Field(default=False)
    found_at: datetime = Field(default_factory=datetime.now)


class DeploymentManifest(BaseModel):
    """Deployment configuration."""

    id: UUID = Field(default_factory=uuid4)
    environment: str  # dev, staging, prod
    version: str
    artifacts: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    deployed_at: datetime | None = Field(default=None)
    status: str = Field(default="pending")


class AgentMessage(BaseModel):
    """Message from an agent."""

    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    phase: Phase
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class HumanApproval(BaseModel):
    """Human approval request/response."""

    id: UUID = Field(default_factory=uuid4)
    phase: Phase
    request_description: str
    artifacts_to_review: list[str] = Field(default_factory=list)
    approved: bool | None = Field(default=None)
    feedback: str | None = Field(default=None)
    requested_at: datetime = Field(default_factory=datetime.now)
    responded_at: datetime | None = Field(default=None)


# =============================================================================
# Main SDLC State (Used by LangGraph)
# =============================================================================


class SDLCState(BaseModel):
    """
    Main state object for the SDLC orchestrator graph.
    
    This state flows through all agents and accumulates artifacts
    as the project progresses through each phase.
    """

    # Core identifiers
    project_id: UUID = Field(default_factory=uuid4)
    project_name: str = Field(default="Untitled Project")

    # Current phase tracking
    current_phase: Phase = Field(default=Phase.REQUIREMENTS)
    phase_history: list[Phase] = Field(default_factory=list)

    # Message history (uses LangGraph's message reducer)
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Requirements phase artifacts
    objective: ProjectObjective | None = Field(default=None)

    # Planning phase artifacts
    epics: list[Epic] = Field(default_factory=list)

    # Architecture phase artifacts
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list)
    system_design: str | None = Field(default=None)

    # Development phase artifacts
    code_artifacts: list[CodeArtifact] = Field(default_factory=list)

    # Code review artifacts
    review_comments: list[CodeReviewComment] = Field(default_factory=list)
    review_approved: bool = Field(default=False)

    # Testing phase artifacts
    test_cases: list[TestCase] = Field(default_factory=list)
    test_results: list[TestResult] = Field(default_factory=list)

    # Security phase artifacts
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    security_approved: bool = Field(default=False)

    # Deployment phase artifacts
    deployment_manifest: DeploymentManifest | None = Field(default=None)

    # Human-in-the-loop
    pending_approvals: list[HumanApproval] = Field(default_factory=list)

    # Agent communication log
    agent_messages: list[AgentMessage] = Field(default_factory=list)

    # Error tracking
    errors: list[str] = Field(default_factory=list)
    retry_count: int = Field(default=0)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = Field(default=None)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def add_agent_message(self, agent_name: str, content: str, **metadata: Any) -> None:
        """Add an agent message to the log."""
        self.agent_messages.append(
            AgentMessage(
                agent_name=agent_name,
                phase=self.current_phase,
                content=content,
                metadata=metadata,
            )
        )
        self.updated_at = datetime.now()

    def transition_to_phase(self, new_phase: Phase) -> None:
        """Transition to a new phase."""
        self.phase_history.append(self.current_phase)
        self.current_phase = new_phase
        self.updated_at = datetime.now()

    def get_stories_by_status(self, status: StoryStatus) -> list[Story]:
        """Get all stories with a specific status."""
        stories = []
        for epic in self.epics:
            stories.extend([s for s in epic.stories if s.status == status])
        return stories

    def get_current_story(self) -> Story | None:
        """Get the current story being worked on."""
        in_progress = self.get_stories_by_status(StoryStatus.IN_PROGRESS)
        return in_progress[0] if in_progress else None

    def get_unresolved_security_findings(self) -> list[SecurityFinding]:
        """Get all unresolved security findings."""
        return [f for f in self.security_findings if not f.is_resolved]

    def get_failed_tests(self) -> list[TestResult]:
        """Get all failed test results."""
        return [t for t in self.test_results if not t.passed]
