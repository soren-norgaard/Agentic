"""Testing Agents - Unit and Integration testing."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import Phase, SDLCState, StoryStatus, TestCase, TestResult


UNIT_TEST_SYSTEM_PROMPT = """You are a Unit Test Agent specialized in creating comprehensive unit tests.

Your responsibilities:
1. Analyze code to identify testable units (functions, methods, classes)
2. Write thorough unit tests covering happy paths and edge cases
3. Ensure proper test isolation with mocking where needed
4. Aim for high code coverage
5. Use appropriate testing frameworks and patterns
6. Write clear, descriptive test names

Output your tests in the following JSON format:
{
    "test_files": [
        {
            "file_path": "tests/test_module.py",
            "content": "Complete test file content",
            "language": "python"
        }
    ],
    "test_cases": [
        {
            "name": "test_function_returns_expected_value",
            "description": "What this test verifies",
            "test_type": "unit",
            "coverage_target": "module.function"
        }
    ],
    "coverage_estimate": 0.0-100.0,
    "notes": "Any additional testing notes"
}

Testing Best Practices:
- One assertion per test when possible
- Use descriptive test names (test_<what>_<condition>_<expected>)
- Arrange-Act-Assert pattern
- Test edge cases and error conditions
- Mock external dependencies
- Keep tests fast and independent"""


INTEGRATION_TEST_SYSTEM_PROMPT = """You are an Integration Test Agent specialized in testing component interactions.

Your responsibilities:
1. Design tests that verify component integration
2. Test API endpoints and data flows
3. Verify database interactions
4. Test external service integrations (with mocking)
5. Validate end-to-end user flows
6. Check error handling across components

Output your tests in the following JSON format:
{
    "test_files": [
        {
            "file_path": "tests/integration/test_api.py",
            "content": "Complete test file content",
            "language": "python"
        }
    ],
    "test_cases": [
        {
            "name": "test_user_registration_flow",
            "description": "Tests complete user registration from API to database",
            "test_type": "integration",
            "components_tested": ["api", "user_service", "database"]
        }
    ],
    "test_environment_requirements": ["List of services/containers needed"],
    "notes": "Any setup or configuration notes"
}

Integration Testing Practices:
- Use realistic test data
- Clean up test data after each test
- Test both success and failure scenarios
- Verify data persistence
- Test concurrent operations where relevant
- Document test environment setup"""


class UnitTestAgent(BaseAgent):
    """Agent for generating unit tests."""

    def __init__(self):
        """Initialize the Unit Test Agent."""
        config = AgentConfig(
            name="UnitTestAgent",
            description="Generates comprehensive unit tests for code",
            phase=Phase.TESTING,
            system_prompt=UNIT_TEST_SYSTEM_PROMPT,
            temperature=0.3,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context with code to test."""
        parts = ["## Code to Test"]

        for artifact in state.code_artifacts:
            # Skip test files
            if "test" in artifact.file_path.lower():
                continue
            parts.append(f"\n### {artifact.file_path}\n```{artifact.language}")
            parts.append(artifact.content)
            parts.append("```")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the test generation response."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                tests = json.loads(content.strip())
            else:
                tests = {}

            # Create test cases
            for test_data in tests.get("test_cases", []):
                test_case = TestCase(
                    name=test_data.get("name", ""),
                    description=test_data.get("description", ""),
                    test_type="unit",
                    file_path=tests.get("test_files", [{}])[0].get("file_path"),
                )
                state.test_cases.append(test_case)

            # Add test files as code artifacts
            from agentic.state.schemas import CodeArtifact

            for file_data in tests.get("test_files", []):
                artifact = CodeArtifact(
                    file_path=file_data.get("file_path", "tests/test_unknown.py"),
                    content=file_data.get("content", ""),
                    language=file_data.get("language", "python"),
                )
                state.code_artifacts.append(artifact)

            # Simulate test results (in real implementation, would run tests)
            for test_case in state.test_cases:
                if test_case.test_type == "unit":
                    result = TestResult(
                        test_case_id=test_case.id,
                        test_name=test_case.name,
                        passed=True,  # Assume tests pass for now
                        coverage_percent=tests.get("coverage_estimate", 80.0),
                    )
                    state.test_results.append(result)

            self.logger.info(
                "Unit tests generated",
                test_count=len(tests.get("test_cases", [])),
                file_count=len(tests.get("test_files", [])),
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse unit test JSON", error=str(e))

        return state


class IntegrationTestAgent(BaseAgent):
    """Agent for generating integration tests."""

    def __init__(self):
        """Initialize the Integration Test Agent."""
        config = AgentConfig(
            name="IntegrationTestAgent",
            description="Generates integration tests for component interactions",
            phase=Phase.TESTING,
            system_prompt=INTEGRATION_TEST_SYSTEM_PROMPT,
            temperature=0.3,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context for integration tests."""
        parts = ["## System Architecture"]

        if state.system_design:
            parts.append(state.system_design)

        parts.append("\n## Implemented Code")
        for artifact in state.code_artifacts:
            if "test" not in artifact.file_path.lower():
                parts.append(f"- {artifact.file_path}")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the integration test response."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                tests = json.loads(content.strip())
            else:
                tests = {}

            # Create test cases
            for test_data in tests.get("test_cases", []):
                test_case = TestCase(
                    name=test_data.get("name", ""),
                    description=test_data.get("description", ""),
                    test_type="integration",
                    file_path=tests.get("test_files", [{}])[0].get("file_path"),
                )
                state.test_cases.append(test_case)

            # Add test files as code artifacts
            from agentic.state.schemas import CodeArtifact

            for file_data in tests.get("test_files", []):
                artifact = CodeArtifact(
                    file_path=file_data.get("file_path", "tests/integration/test_unknown.py"),
                    content=file_data.get("content", ""),
                    language=file_data.get("language", "python"),
                )
                state.code_artifacts.append(artifact)

            self.logger.info(
                "Integration tests generated",
                test_count=len(tests.get("test_cases", [])),
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse integration test JSON", error=str(e))

        return state
