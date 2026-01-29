"""Base agent class and utilities."""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from agentic.config import LLMProvider, settings
from agentic.state.schemas import Phase, SDLCState


logger = structlog.get_logger()


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str
    description: str
    phase: Phase
    system_prompt: str
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4096)
    tools: list[Any] = Field(default_factory=list)


class BaseAgent(ABC):
    """
    Base class for all SDLC agents.
    
    Each agent is responsible for a specific phase or task in the SDLC.
    Agents receive state, perform their work, and return updated state.
    """

    def __init__(self, config: AgentConfig):
        """Initialize the agent with configuration."""
        self.config = config
        self.name = config.name
        self.phase = config.phase
        self.llm = self._create_llm()
        self.logger = logger.bind(agent=self.name)

    def _create_llm(self) -> BaseChatModel:
        """Create the LLM instance based on configuration."""
        if settings.llm_provider == LLMProvider.OPENAI:
            return ChatOpenAI(
                model=settings.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=settings.openai_api_key,
            )
        elif settings.llm_provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(
                model=settings.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=settings.anthropic_api_key,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    def _get_system_message(self) -> SystemMessage:
        """Get the system message for this agent."""
        return SystemMessage(content=self.config.system_prompt)

    def _create_prompt(self, state: SDLCState) -> list[SystemMessage | HumanMessage]:
        """Create the prompt messages for the LLM."""
        messages = [self._get_system_message()]

        # Add relevant context from state
        context = self._build_context(state)
        if context:
            messages.append(HumanMessage(content=context))

        return messages

    @abstractmethod
    def _build_context(self, state: SDLCState) -> str:
        """
        Build context string from state for the agent.
        
        Each agent should extract relevant information from state.
        """
        pass

    @abstractmethod
    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """
        Process the LLM response and update state.
        
        Each agent should parse the response and update relevant state fields.
        """
        pass

    async def run(self, state: SDLCState) -> SDLCState:
        """
        Execute the agent's task.
        
        Args:
            state: Current SDLC state
            
        Returns:
            Updated SDLC state
        """
        self.logger.info("Agent starting", phase=self.phase.value)

        try:
            # Build prompt
            messages = self._create_prompt(state)

            # Invoke LLM
            if self.config.tools:
                llm_with_tools = self.llm.bind_tools(self.config.tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)

            # Process response and update state
            updated_state = self._process_response(response, state)

            # Log agent message
            updated_state.add_agent_message(
                agent_name=self.name,
                content=response.content if isinstance(response.content, str) else str(response.content),
            )

            self.logger.info("Agent completed", phase=self.phase.value)
            return updated_state

        except Exception as e:
            self.logger.error("Agent failed", error=str(e), phase=self.phase.value)
            state.errors.append(f"{self.name}: {str(e)}")
            state.retry_count += 1
            return state

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.name}, phase={self.phase.value})"


class ToolResult(BaseModel):
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: str | None = None


def create_agent_node(agent: BaseAgent):
    """
    Create a LangGraph node function from an agent.
    
    This wraps the agent's run method in the format expected by LangGraph.
    """

    async def node(state: dict) -> dict:
        """LangGraph node function."""
        # Convert dict to SDLCState
        sdlc_state = SDLCState(**state)

        # Run agent
        updated_state = await agent.run(sdlc_state)

        # Return updated state as dict
        return updated_state.model_dump()

    return node
