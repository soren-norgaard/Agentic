# =============================================================================
# SDLC Agent - Pytest Configuration
# =============================================================================

import asyncio
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure src is in path for module imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# =============================================================================
# Async Event Loop
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Database
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[Any, None]:
    """Create a fresh test database for each test."""
    # For now, yield None - will be implemented when we add DB tests
    yield None


# =============================================================================
# API Test Client
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing the API."""
    # Import here to avoid issues with missing env vars during collection
    try:
        from sdlc_agent.api.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    except Exception:
        # If app can't be imported, yield a mock client
        yield None


# =============================================================================
# Mock LLM Responses
# =============================================================================

@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Provide a mock LLM response for testing agents."""
    return {
        "content": "This is a mock LLM response for testing.",
        "tool_calls": [],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


# =============================================================================
# Sample Test Data
# =============================================================================

@pytest.fixture
def sample_project() -> dict[str, Any]:
    """Provide sample project data for testing."""
    return {
        "name": "Test Project",
        "description": "A test project for CI",
        "repository_url": "https://github.com/test/test-repo",
    }


@pytest.fixture
def sample_workflow() -> dict[str, Any]:
    """Provide sample workflow data for testing."""
    return {
        "objective": "Build a simple feature",
        "config": {"max_iterations": 10},
    }


@pytest.fixture
def sample_user_story() -> dict[str, Any]:
    """Provide sample user story for testing."""
    return {
        "id": "story-1",
        "title": "User Login",
        "user_story": "As a user, I want to log in so that I can access my account",
        "acceptance_criteria": [
            "User can enter email and password",
            "User receives error for invalid credentials",
            "User is redirected to dashboard on success",
        ],
    }
