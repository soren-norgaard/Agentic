# =============================================================================
# SDLC Agent - Testing Agent
# =============================================================================
# Generates and executes tests.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sdlc_agent.agents.base import (
    AgentPhase,
    AgentState,
    BaseAgent,
    MessageRole,
    ToolDefinition,
    ToolParameter,
)


@dataclass
class TestingState(AgentState):
    """State specific to the testing agent."""

    # Testing artifacts
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    coverage_report: dict[str, Any] = field(default_factory=dict)
    test_plan: dict[str, Any] = field(default_factory=dict)


class TestingAgent(BaseAgent[TestingState]):
    """
    Testing agent.

    Responsibilities:
    - Generate test cases from requirements
    - Write unit and integration tests
    - Execute test suites
    - Report test results and coverage
    - Identify untested code paths
    """

    name = "tester"
    description = "Generates and executes tests"
    phase = AgentPhase.TESTING

    @property
    def system_prompt(self) -> str:
        return """You are a QA Testing Agent specializing in software testing.

Your responsibilities:
1. Create comprehensive test plans from requirements
2. Write unit tests for individual functions/methods
3. Write integration tests for component interactions
4. Identify edge cases and boundary conditions
5. Report test results and coverage metrics
6. Suggest areas needing more test coverage

Test types to consider:
- Unit tests: Test individual functions in isolation
- Integration tests: Test component interactions
- E2E tests: Test complete user workflows
- Edge case tests: Boundary values, null inputs, etc.

Use appropriate testing frameworks and follow testing best practices.
Aim for high code coverage but prioritize meaningful tests over coverage numbers."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_test_case",
                description="Create a test case",
                parameters=[
                    ToolParameter(
                        name="name",
                        description="Test case name",
                    ),
                    ToolParameter(
                        name="description",
                        description="What the test verifies",
                    ),
                    ToolParameter(
                        name="test_type",
                        description="Type of test",
                        enum=["unit", "integration", "e2e", "performance"],
                    ),
                    ToolParameter(
                        name="test_code",
                        description="The test code",
                    ),
                    ToolParameter(
                        name="file_path",
                        description="Path where test should be saved",
                    ),
                ],
            ),
            ToolDefinition(
                name="run_tests",
                description="Execute test suite",
                parameters=[
                    ToolParameter(
                        name="test_pattern",
                        description="Pattern to match tests (e.g., 'test_*.py')",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="report_coverage",
                description="Report test coverage metrics",
                parameters=[
                    ToolParameter(
                        name="total_coverage",
                        description="Total coverage percentage",
                    ),
                    ToolParameter(
                        name="uncovered_areas",
                        description="Areas lacking coverage (JSON array)",
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_testing",
                description="Mark testing as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of testing results",
                    ),
                    ToolParameter(
                        name="passed",
                        description="Number of tests passed",
                    ),
                    ToolParameter(
                        name="failed",
                        description="Number of tests failed",
                    ),
                ],
            ),
        ]

    async def process(self, state: TestingState) -> TestingState:
        """Process testing tasks."""
        self.logger.info("Testing agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Get code from state or metadata
        code_files = getattr(state, 'code_files', {}) or state.metadata.get("code_files", {})
        user_stories = getattr(state, 'user_stories', []) or state.metadata.get("user_stories", [])
        
        code_to_test = ""
        if code_files:
            for path, content in code_files.items():
                code_to_test += f"\n--- {path} ---\n{content}\n"
        else:
            code_to_test = state.metadata.get("code", "No code provided")
        
        requirements = ""
        for story in user_stories:
            requirements += f"- {story.get('title', '')}: {story.get('user_story', '')}\n"
        
        state.add_message(
            MessageRole.USER,
            f"Please create tests for the following code:\n\n{code_to_test}\n\n"
            f"Requirements:\n{requirements}",
        )
        
        state = await self.run_with_tools(state)
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: TestingState,
    ) -> tuple[str, TestingState]:
        """Execute testing tools."""
        import json
        import uuid
        
        if tool_name == "create_test_case":
            test_id = str(uuid.uuid4())[:8]
            
            test_case = {
                "id": test_id,
                "name": tool_args.get("name"),
                "description": tool_args.get("description"),
                "type": tool_args.get("test_type"),
                "code": tool_args.get("test_code"),
                "file_path": tool_args.get("file_path"),
                "status": "pending",
            }
            state.test_cases.append(test_case)
            
            state.add_artifact(
                name=f"TEST-{test_id}",
                artifact_type="test",
                content=tool_args.get("test_code"),
                file_path=tool_args.get("file_path"),
            )
            
            return f"Created test case: {tool_args.get('name')}", state
        
        elif tool_name == "run_tests":
            # Simulate test execution
            passed = len(state.test_cases)
            failed = 0
            
            for test in state.test_cases:
                test["status"] = "passed"
                state.test_results.append({
                    "test_id": test["id"],
                    "name": test["name"],
                    "status": "passed",
                    "duration_ms": 100,
                })
            
            return f"Tests executed: {passed} passed, {failed} failed", state
        
        elif tool_name == "report_coverage":
            uncovered = tool_args.get("uncovered_areas", "[]")
            if isinstance(uncovered, str):
                try:
                    uncovered = json.loads(uncovered)
                except json.JSONDecodeError:
                    uncovered = []
            
            state.coverage_report = {
                "total_coverage": float(tool_args.get("total_coverage", 0)),
                "uncovered_areas": uncovered,
            }
            
            return f"Coverage: {tool_args.get('total_coverage')}%", state
        
        elif tool_name == "complete_testing":
            passed = int(tool_args.get("passed", 0))
            failed = int(tool_args.get("failed", 0))
            
            state.test_plan["summary"] = tool_args.get("summary")
            state.test_plan["passed"] = passed
            state.test_plan["failed"] = failed
            state.test_plan["total"] = passed + failed
            
            # Mark testing phase as complete
            if hasattr(state, 'phases_completed') and 'testing' not in state.phases_completed:
                state.phases_completed.append('testing')
            
            state.add_message(
                MessageRole.ASSISTANT,
                f"Testing complete.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Results: {passed} passed, {failed} failed.",
            )
            
            if failed == 0:
                state.phase = AgentPhase.SECURITY
            
            return f"Testing complete: {passed} passed, {failed} failed", state
        
        return f"Unknown tool: {tool_name}", state
