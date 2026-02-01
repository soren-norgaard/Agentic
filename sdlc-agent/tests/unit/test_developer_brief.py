# =============================================================================
# SDLC Agent - Unit Tests for Developer Brief
# =============================================================================

import pytest

from sdlc_agent.agents.developer import DeveloperBrief


class TestDeveloperBrief:
    """Tests for DeveloperBrief dataclass."""

    def test_basic_brief_creation(self):
        """Test basic developer brief creation."""
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="User Login",
        )
        
        assert brief.story_id == "story-1"
        assert brief.story_title == "User Login"
        assert brief.test_stubs == []
        assert brief.test_stubs_artifact_id is None

    def test_brief_with_test_stubs(self):
        """Test developer brief with test stubs."""
        test_stubs = [
            {
                "name": "test_user_login",
                "file_path": "tests/test_auth.py",
                "skeleton_code": "def test_user_login():\n    # TODO: Implement\n    pass",
            },
            {
                "name": "test_user_logout",
                "file_path": "tests/test_auth.py",
                "skeleton_code": "def test_user_logout():\n    # TODO: Implement\n    pass",
            },
        ]
        
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="User Authentication",
            test_stubs=test_stubs,
            test_stubs_artifact_id="artifact-123",
        )
        
        assert len(brief.test_stubs) == 2
        assert brief.test_stubs_artifact_id == "artifact-123"

    def test_to_markdown_includes_test_stubs(self):
        """Test that to_markdown includes test stubs section."""
        test_stubs = [
            {
                "name": "test_login_success",
                "file_path": "tests/test_auth.py",
                "skeleton_code": "def test_login_success():\n    # TODO: Test successful login\n    pass",
            },
        ]
        
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="User Login",
            test_stubs=test_stubs,
            test_stubs_artifact_id="TEST-STUB-abc123",
        )
        
        markdown = brief.to_markdown()
        
        assert "Test Stubs" in markdown
        assert "test_login_success" in markdown
        assert "tests/test_auth.py" in markdown
        assert "TEST-STUB-abc123" in markdown
        assert "TDD" in markdown or "Implement Alongside Code" in markdown

    def test_to_markdown_without_test_stubs(self):
        """Test that to_markdown works without test stubs."""
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="Simple Feature",
            acceptance_criteria=["Feature works correctly"],
        )
        
        markdown = brief.to_markdown()
        
        # Should not have test stubs section
        assert "Test Stubs" not in markdown or "🧬" not in markdown
        # Should still have other sections
        assert "Developer Brief" in markdown
        assert "Simple Feature" in markdown

    def test_to_markdown_includes_all_sections(self):
        """Test that to_markdown includes all configured sections."""
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="Full Feature",
            requirements_addressed=["REQ-1", "REQ-2"],
            acceptance_criteria=["AC1", "AC2"],
            architecture_context="Uses MVC pattern",
            files_to_create=[{"path": "src/new.py", "purpose": "New module"}],
            files_to_modify=[{"path": "src/existing.py", "changes": "Add method"}],
            suggested_approach="Start with tests",
            implementation_steps=["Step 1", "Step 2"],
            potential_challenges=["Challenge 1"],
            coding_standards=["Use type hints"],
            testing_requirements=["80% coverage"],
            test_stubs=[
                {"name": "test_feature", "file_path": "tests/test_feature.py", "skeleton_code": "# test"}
            ],
            pre_implementation_checklist=["Check 1"],
            definition_of_done=["Done criteria 1"],
        )
        
        markdown = brief.to_markdown()
        
        # Check all major sections
        assert "Requirements Traceability" in markdown
        assert "Acceptance Criteria" in markdown
        assert "Architecture Context" in markdown
        assert "Files to Create" in markdown
        assert "Files to Modify" in markdown
        assert "Suggested Approach" in markdown
        assert "Implementation Steps" in markdown
        assert "Potential Challenges" in markdown
        assert "Coding Standards" in markdown
        assert "Testing Requirements" in markdown
        assert "Test Stubs" in markdown
        assert "Pre-Implementation Checklist" in markdown
        assert "Definition of Done" in markdown


class TestDeveloperBriefTDDIntegration:
    """Tests for TDD integration in developer briefs."""

    def test_implementation_steps_reference_tests(self):
        """Test that implementation steps mention test stubs when present."""
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="TDD Feature",
            test_stubs=[
                {"name": "test_tdd", "file_path": "tests/test_tdd.py", "skeleton_code": "pass"}
            ],
            implementation_steps=[
                "Review test stubs",
                "Implement feature",
                "Make tests pass",
            ],
        )
        
        markdown = brief.to_markdown()
        
        # Implementation steps should be present
        assert "Implementation Steps" in markdown
        assert "Review test stubs" in markdown or "test" in markdown.lower()

    def test_definition_of_done_includes_tests(self):
        """Test that DoD mentions test implementation when stubs present."""
        brief = DeveloperBrief(
            story_id="story-1",
            story_title="TDD Feature",
            test_stubs=[
                {"name": "test_feature", "file_path": "tests/test.py", "skeleton_code": "pass"}
            ],
            definition_of_done=[
                "All test stubs implemented",
                "All tests pass",
            ],
        )
        
        markdown = brief.to_markdown()
        
        assert "Definition of Done" in markdown
        assert "test" in markdown.lower()
