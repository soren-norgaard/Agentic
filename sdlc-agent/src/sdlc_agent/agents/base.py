# =============================================================================
# SDLC Agent - Base Agent Framework
# =============================================================================
# Base classes and utilities for building LangGraph-based agents.
# =============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# State Types
# =============================================================================


class MessageRole(str, Enum):
    """Message roles in agent conversations."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the agent conversation."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for LLM."""
        result = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result


class AgentPhase(str, Enum):
    """SDLC phases an agent can be in."""

    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    DESIGN = "design"
    DEVELOPMENT = "development"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


@dataclass
class AgentState:
    """
    Base state for all agents.

    This is the core state that flows through the LangGraph.
    """

    # Workflow identification
    workflow_id: str
    project_id: str

    # Current phase
    phase: AgentPhase

    # Conversation history
    messages: list[Message] = field(default_factory=list)

    # Task context
    current_task: dict[str, Any] | None = None
    task_queue: list[dict[str, Any]] = field(default_factory=list)
    completed_tasks: list[dict[str, Any]] = field(default_factory=list)

    # Artifacts produced
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    # Error tracking
    errors: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0

    # Human-in-the-loop
    awaiting_human_input: bool = False
    human_input_request: dict[str, Any] | None = None
    human_input_response: dict[str, Any] | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    iteration_count: int = 0
    tokens_used: int = 0

    def add_message(self, role: MessageRole, content: str, **kwargs: Any) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content, **kwargs))

    def add_error(self, error_type: str, message: str, **details: Any) -> None:
        """Record an error."""
        self.errors.append(
            {
                "type": error_type,
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
                **details,
            }
        )

    def add_artifact(
        self,
        name: str,
        artifact_type: str,
        content: str | None = None,
        **metadata: Any,
    ) -> None:
        """Record a produced artifact."""
        self.artifacts.append(
            {
                "name": name,
                "type": artifact_type,
                "content": content,
                "created_at": datetime.now(UTC).isoformat(),
                **metadata,
            }
        )


StateT = TypeVar("StateT", bound=AgentState)


# =============================================================================
# Tool Definition
# =============================================================================


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str
    description: str
    type: str = "string"
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool available to an agent."""

    name: str
    description: str
    parameters: list[ToolParameter]

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# =============================================================================
# Base Agent
# =============================================================================


class BaseAgent(ABC, Generic[StateT]):
    """
    Abstract base class for all SDLC agents.

    Agents are responsible for:
    1. Processing the current state
    2. Making LLM calls with tools
    3. Updating the state
    4. Determining the next action
    """

    name: str = "base_agent"
    description: str = "Base agent"
    phase: AgentPhase = AgentPhase.REQUIREMENTS

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = get_logger(f"agent.{self.name}")

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent."""
        ...

    @property
    def tools(self) -> list[ToolDefinition]:
        """Tools available to this agent."""
        return []

    @abstractmethod
    async def process(self, state: StateT) -> StateT:
        """
        Process the current state and return updated state.

        Args:
            state: Current agent state

        Returns:
            Updated agent state
        """
        ...

    async def should_continue(self, state: StateT) -> bool:
        """
        Determine if the agent should continue processing.

        Args:
            state: Current agent state

        Returns:
            True if processing should continue
        """
        # Stop if awaiting human input
        if state.awaiting_human_input:
            return False

        # Stop if current task is complete
        if state.current_task and state.current_task.get("status") == "complete":
            return False

        # Stop if too many errors
        if len(state.errors) > 3:
            return False

        return True

    def get_next_agent(self, state: StateT) -> str | None:
        """
        Determine the next agent to hand off to.

        Args:
            state: Current agent state

        Returns:
            Name of next agent, or None to end
        """
        return None

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Make an LLM call using the unified LLM client.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions

        Returns:
            LLM response with content and/or tool_calls
        """
        from sdlc_agent.services import get_llm_client
        
        client = get_llm_client()
        
        response = await client.chat(
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
        )
        
        return {
            "content": response.content,
            "tool_calls": response.tool_calls,
            "tokens_used": response.tokens_used,
            "finish_reason": response.finish_reason,
        }

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: StateT,
    ) -> tuple[str, StateT]:
        """
        Execute a tool and return the result.
        
        Override in subclasses to implement tool execution.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            state: Current agent state
            
        Returns:
            Tuple of (result_string, updated_state)
        """
        return f"Tool '{tool_name}' not implemented", state

    async def run_with_tools(self, state: StateT, max_iterations: int = 10) -> StateT:
        """
        Run the agent with tool support until completion.
        
        Args:
            state: Initial agent state
            max_iterations: Maximum tool call iterations
            
        Returns:
            Final agent state
        """
        # Build messages from state
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in state.messages:
            messages.append(msg.to_dict())
        
        # Get tools schema
        tools = [t.to_openai_schema() for t in self.tools] if self.tools else None
        
        for iteration in range(max_iterations):
            state.iteration_count += 1
            
            self.logger.info(
                "Agent iteration",
                agent=self.name,
                iteration=iteration + 1,
                message_count=len(messages),
            )
            
            # Call LLM
            response = await self._call_llm(messages, tools)
            state.tokens_used += response.get("tokens_used", 0)
            
            # Handle tool calls
            if response.get("tool_calls"):
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.get("content") or "",
                    "tool_calls": response["tool_calls"],
                })
                
                # Execute each tool
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    try:
                        tool_args = __import__("json").loads(tool_call["function"]["arguments"])
                    except __import__("json").JSONDecodeError:
                        tool_args = {}
                    
                    self.logger.info(
                        "Executing tool",
                        tool=tool_name,
                        args=tool_args,
                    )
                    
                    result, state = await self._execute_tool(tool_name, tool_args, state)
                    
                    # Add tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    })
            else:
                # No tool calls - agent is done
                if response.get("content"):
                    state.add_message(MessageRole.ASSISTANT, response["content"])
                break
        
        return state
