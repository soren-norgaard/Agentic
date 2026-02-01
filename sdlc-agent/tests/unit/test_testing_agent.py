# =============================================================================
# SDLC Agent - Unit Tests for Testing Agent
# =============================================================================

import pytest
from unittest.mock import AsyncMock, patch

from sdlc_agent.agents.tester import TestingAgent, TestingState
from sdlc_agent.agents.base import AgentPhase


def make_testing_state(**kwargs) -> TestingState:
    """Helper to create TestingState with required defaults."""
    defaults = {
        "workflow_id": "test-workflow-123",
        "project_id": "test-project-123",
        "phase": AgentPhase.TESTING,
    }
    defaults.update(kwargs)
    return TestingState(**defaults)


class TestTestingState:
    """Tests for TestingState dataclass."""

    def test_default_state(self):
        """Test default state initialization."""
        state = make_testing_state()
        
        assert state.workflow_id == "test-workflow-123"
        assert state.project_id == "test-project-123"
        assert state.phase == AgentPhase.TESTING
        assert state.test_stubs == []
        assert state.test_stubs_generated is False
        assert state.stub_mode is False
        assert state.test_cases == []
        assert state.test_results == []
        assert state.coverage_report == {}
        assert state.test_plan == {}

    def test_stub_mode_state(self):
        """Test state with stub mode enabled."""
        state = make_testing_state(
            stub_mode=True,
            test_stubs=[
                {"id": "stub-1", "name": "test_login", "description": "Test login"}
            ],
        )
        
        assert state.stub_mode is True
        assert len(state.test_stubs) == 1
        assert state.test_stubs[0]["name"] == "test_login"


class TestTestingAgent:
    """Tests for TestingAgent."""

    def test_agent_properties(self):
        """Test agent basic properties."""
        agent = TestingAgent()
        
        assert agent.name == "tester"
        assert agent.description == "Generates and executes tests"
        assert agent.phase == AgentPhase.TESTING

    def test_system_prompt_contains_modes(self):
        """Test that system prompt describes both modes."""
        agent = TestingAgent()
        prompt = agent.system_prompt
        
        assert "STUB MODE" in prompt
        assert "FULL MODE" in prompt
        assert "TDD" in prompt or "test stubs" in prompt.lower()

    def test_tools_include_stub_tools(self):
        """Test that tools include stub generation tools."""
        agent = TestingAgent()
        tool_names = [t.name for t in agent.tools]
        
        assert "create_test_plan" in tool_names
        assert "create_test_stub" in tool_names
        assert "complete_stub_generation" in tool_names

    def test_tools_include_full_mode_tools(self):
        """Test that tools include full testing tools."""
        agent = TestingAgent()
        tool_names = [t.name for t in agent.tools]
        
        assert "create_test_case" in tool_names
        assert "run_tests" in tool_names
        assert "report_coverage" in tool_names
        assert "complete_testing" in tool_names


class TestToolExecution:
    """Tests for TestingAgent tool execution."""

    @pytest.mark.asyncio
    async def test_create_test_stub(self):
        """Test create_test_stub tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        
        tool_args = {
            "name": "test_user_login",
            "description": "Test user login functionality",
            "test_type": "unit",
            "skeleton_code": "def test_user_login():\n    # TODO: Implement test\n    pass",
            "file_path": "tests/test_auth.py",
            "acceptance_criteria_ref": "User can login",
        }
        
        result, new_state = await agent._execute_tool("create_test_stub", tool_args, state)
        
        assert "Created test stub" in result
        assert len(new_state.test_stubs) == 1
        assert new_state.test_stubs[0]["name"] == "test_user_login"
        assert new_state.test_stubs[0]["status"] == "stub"

    @pytest.mark.asyncio
    async def test_create_test_plan(self):
        """Test create_test_plan tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        
        tool_args = {
            "story_id": "story-1",
            "test_strategy": "Unit tests for core logic, integration tests for API",
            "test_categories": '["unit", "integration"]',
            "acceptance_test_outline": "Verify all acceptance criteria",
        }
        
        result, new_state = await agent._execute_tool("create_test_plan", tool_args, state)
        
        assert "Created test plan" in result
        assert new_state.test_plan["story_id"] == "story-1"
        assert new_state.test_plan["strategy"] == tool_args["test_strategy"]

    @pytest.mark.asyncio
    async def test_complete_stub_generation(self):
        """Test complete_stub_generation tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        state.test_stubs = [{"id": "1", "name": "test_1"}, {"id": "2", "name": "test_2"}]
        
        tool_args = {
            "summary": "Generated 2 test stubs for login feature",
            "stub_count": "2",
        }
        
        result, new_state = await agent._execute_tool("complete_stub_generation", tool_args, state)
        
        assert "Stub generation complete" in result
        assert new_state.test_stubs_generated is True
        assert new_state.test_plan["stub_count"] == 2

    @pytest.mark.asyncio
    async def test_create_test_case(self):
        """Test create_test_case tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        
        tool_args = {
            "name": "test_user_login_success",
            "description": "Test successful user login",
            "test_type": "unit",
            "test_code": "def test_user_login_success():\n    assert login('user', 'pass') == True",
            "file_path": "tests/test_auth.py",
        }
        
        result, new_state = await agent._execute_tool("create_test_case", tool_args, state)
        
        assert "Created test case" in result
        assert len(new_state.test_cases) == 1
        assert new_state.test_cases[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_run_tests(self):
        """Test run_tests tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        state.test_cases = [
            {"id": "1", "name": "test_1", "status": "pending"},
            {"id": "2", "name": "test_2", "status": "pending"},
        ]
        
        result, new_state = await agent._execute_tool("run_tests", {}, state)
        
        assert "Tests executed" in result
        assert "2 passed" in result
        assert len(new_state.test_results) == 2
        for test in new_state.test_cases:
            assert test["status"] == "passed"

    @pytest.mark.asyncio
    async def test_report_coverage(self):
        """Test report_coverage tool execution."""
        agent = TestingAgent()
        state = make_testing_state()
        
        tool_args = {
            "total_coverage": "85.5",
            "uncovered_areas": '["auth.py:45-50", "utils.py:100-110"]',
        }
        
        result, new_state = await agent._execute_tool("report_coverage", tool_args, state)
        
        assert "Coverage: 85.5%" in result
        assert new_state.coverage_report["total_coverage"] == 85.5
        assert len(new_state.coverage_report["uncovered_areas"]) == 2
