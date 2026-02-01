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
    test_stubs: list[dict[str, Any]] = field(default_factory=list)  # Early test skeletons
    test_stubs_generated: bool = False  # Flag for early stub generation
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    coverage_report: dict[str, Any] = field(default_factory=dict)
    test_plan: dict[str, Any] = field(default_factory=dict)
    
    # Mode control
    stub_mode: bool = False  # If True, generate stubs only (early phase)


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

You operate in TWO modes:

## STUB MODE (Early Phase - During Planning/Development)
When generating test stubs BEFORE code is written:
1. Create a test plan based on requirements and acceptance criteria
2. Generate test skeleton/stubs that developers implement alongside code
3. Focus on WHAT should be tested, not HOW (implementation details come later)
4. Use `create_test_plan` and `create_test_stub` tools

## FULL MODE (Testing Phase - After Development)
When writing complete tests AFTER code exists:
1. Write full unit tests for individual functions/methods
2. Write integration tests for component interactions
3. Execute test suites and report results
4. Report coverage metrics
5. Use `create_test_case`, `run_tests`, `report_coverage`, `complete_testing` tools

Test types to consider:
- Unit tests: Test individual functions in isolation
- Integration tests: Test component interactions
- E2E tests: Test complete user workflows
- Edge case tests: Boundary values, null inputs, etc.

Use appropriate testing frameworks (pytest for Python, Jest/Vitest for TypeScript).
Aim for high code coverage but prioritize meaningful tests over coverage numbers."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            # STUB MODE tools (early phase)
            ToolDefinition(
                name="create_test_plan",
                description="Create a test plan from requirements (STUB MODE - early phase)",
                parameters=[
                    ToolParameter(
                        name="story_id",
                        description="The story/feature ID this plan covers",
                    ),
                    ToolParameter(
                        name="test_strategy",
                        description="Overall testing strategy and approach",
                    ),
                    ToolParameter(
                        name="test_categories",
                        description="JSON array of test categories with descriptions",
                    ),
                    ToolParameter(
                        name="acceptance_test_outline",
                        description="How acceptance criteria will be verified",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_test_stub",
                description="Create a test skeleton/stub for TDD (STUB MODE - early phase)",
                parameters=[
                    ToolParameter(
                        name="name",
                        description="Test stub name (e.g., 'test_user_registration')",
                    ),
                    ToolParameter(
                        name="description",
                        description="What this test should verify once implemented",
                    ),
                    ToolParameter(
                        name="test_type",
                        description="Type of test",
                        enum=["unit", "integration", "e2e", "performance"],
                    ),
                    ToolParameter(
                        name="skeleton_code",
                        description="Test skeleton with TODO comments showing what to test",
                    ),
                    ToolParameter(
                        name="file_path",
                        description="Path where test file should be created",
                    ),
                    ToolParameter(
                        name="acceptance_criteria_ref",
                        description="Which acceptance criteria this test covers",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_stub_generation",
                description="Mark test stub generation as complete (STUB MODE)",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of test stubs generated",
                    ),
                    ToolParameter(
                        name="stub_count",
                        description="Number of test stubs created",
                    ),
                ],
            ),
            # FULL MODE tools (testing phase)
            ToolDefinition(
                name="create_test_case",
                description="Create a complete test case with full implementation (FULL MODE)",
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
                        description="The complete test code",
                    ),
                    ToolParameter(
                        name="file_path",
                        description="Path where test should be saved",
                    ),
                ],
            ),
            ToolDefinition(
                name="run_tests",
                description="Execute test suite (FULL MODE)",
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
                description="Report test coverage metrics (FULL MODE)",
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
                description="Mark testing as complete (FULL MODE)",
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
        self.logger.info(
            "Testing agent processing", 
            workflow_id=state.workflow_id,
            stub_mode=getattr(state, 'stub_mode', False)
        )
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Check if we're in stub mode (early phase)
        stub_mode = getattr(state, 'stub_mode', False)
        
        if stub_mode:
            # STUB MODE: Generate test skeletons from requirements
            user_stories = getattr(state, 'user_stories', []) or state.metadata.get("user_stories", [])
            tasks = getattr(state, 'tasks', []) or state.metadata.get("tasks", [])
            
            requirements = "## User Stories:\n"
            for story in user_stories:
                title = story.get('title', '')
                user_story_text = story.get('user_story', '')
                acceptance = story.get('acceptance_criteria', [])
                requirements += f"\n### {title}\n{user_story_text}\n"
                if acceptance:
                    requirements += "Acceptance Criteria:\n"
                    for ac in acceptance:
                        requirements += f"- {ac}\n"
            
            if tasks:
                requirements += "\n## Tasks:\n"
                for task in tasks[:10]:  # Limit to first 10
                    requirements += f"- {task.get('title', '')}: {task.get('description', '')}\n"
            
            state.add_message(
                MessageRole.USER,
                f"""You are in STUB MODE. Generate test stubs (skeletons) for the following requirements.

DO NOT write complete test implementations. Instead:
1. Create a test_plan with overall strategy
2. Create test_stubs with skeleton code containing TODO comments
3. Focus on WHAT should be tested based on acceptance criteria
4. Call complete_stub_generation when done

{requirements}

Generate test stubs that developers will implement alongside the code (TDD approach).""",
            )
        else:
            # FULL MODE: Create complete tests for existing code
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
                f"""You are in FULL MODE. Create complete test implementations for the following code.

Write full test code, execute tests, and report coverage.

Code to test:
{code_to_test}

Requirements:
{requirements}""",
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
        
        # =================================================================
        # STUB MODE TOOLS (Early Phase)
        # =================================================================
        
        if tool_name == "create_test_plan":
            story_id = tool_args.get("story_id", "unknown")
            
            categories = tool_args.get("test_categories", "[]")
            if isinstance(categories, str):
                try:
                    categories = json.loads(categories)
                except json.JSONDecodeError:
                    categories = []
            
            state.test_plan = {
                "story_id": story_id,
                "strategy": tool_args.get("test_strategy"),
                "categories": categories,
                "acceptance_test_outline": tool_args.get("acceptance_test_outline"),
                "created_at": "early_phase",
            }
            
            # Create test_plan artifact
            plan_content = f"""# Test Plan for {story_id}

## Strategy
{tool_args.get('test_strategy', '')}

## Test Categories
{json.dumps(categories, indent=2) if categories else 'None specified'}

## Acceptance Test Outline
{tool_args.get('acceptance_test_outline', '')}
"""
            state.add_artifact(
                name=f"TEST-PLAN-{story_id}",
                artifact_type="test_plan",
                content=plan_content,
            )
            
            return f"Created test plan for {story_id}", state
        
        elif tool_name == "create_test_stub":
            stub_id = str(uuid.uuid4())[:8]
            
            test_stub = {
                "id": stub_id,
                "name": tool_args.get("name"),
                "description": tool_args.get("description"),
                "type": tool_args.get("test_type"),
                "skeleton_code": tool_args.get("skeleton_code"),
                "file_path": tool_args.get("file_path"),
                "acceptance_criteria_ref": tool_args.get("acceptance_criteria_ref"),
                "status": "stub",
            }
            state.test_stubs.append(test_stub)
            
            # Create test_stub artifact
            state.add_artifact(
                name=f"TEST-STUB-{stub_id}",
                artifact_type="test_stub",
                content=tool_args.get("skeleton_code"),
                file_path=tool_args.get("file_path"),
            )
            
            return f"Created test stub: {tool_args.get('name')}", state
        
        elif tool_name == "complete_stub_generation":
            stub_count = int(tool_args.get("stub_count", len(state.test_stubs)))
            
            state.test_stubs_generated = True
            state.test_plan["stub_summary"] = tool_args.get("summary")
            state.test_plan["stub_count"] = stub_count
            
            state.add_message(
                MessageRole.ASSISTANT,
                f"Test stub generation complete.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Stubs created: {stub_count}",
            )
            
            return f"Stub generation complete: {stub_count} stubs created", state
        
        # =================================================================
        # FULL MODE TOOLS (Testing Phase)
        # =================================================================
        
        elif tool_name == "create_test_case":
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
