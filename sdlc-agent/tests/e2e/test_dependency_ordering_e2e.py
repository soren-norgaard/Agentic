# =============================================================================
# End-to-End Tests for Task Dependency Ordering
# =============================================================================
# Tests verify that dependency-aware task ordering works correctly in the
# full SDLC workflow, ensuring developers work on tasks in correct order.
# =============================================================================

import pytest
import sys
from pathlib import Path
import importlib.util

# Load task_ordering module directly to avoid heavy services/__init__.py dependencies
_task_ordering_path = Path(__file__).parent.parent.parent / "src/sdlc_agent/services/task_ordering.py"
_spec = importlib.util.spec_from_file_location("task_ordering", _task_ordering_path)
_task_ordering = importlib.util.module_from_spec(_spec)
sys.modules["task_ordering"] = _task_ordering
_spec.loader.exec_module(_task_ordering)

DependencyGraph = _task_ordering.DependencyGraph
TaskReadiness = _task_ordering.TaskReadiness
build_dependency_graph = _task_ordering.build_dependency_graph
get_ordered_tasks = _task_ordering.get_ordered_tasks


class TestDependencyOrderingE2E:
    """
    End-to-end tests for dependency-aware task ordering.
    
    These tests simulate realistic planning scenarios and verify
    that developers see tasks in the correct order.
    """

    @pytest.mark.e2e
    def test_full_project_workflow_ordering(self):
        """
        Simulate a full project planning with dependencies.
        
        Project: E-commerce checkout feature
        - M1: Database schema must be created first
        - M2: API endpoints depend on schema
        - M3: Frontend depends on API
        - M4: Tests depend on all above
        """
        # Tasks as would be created by PlanningAgent
        tasks = [
            # Milestone 1: Database
            {"id": "db-1", "title": "Design checkout schema", "status": "backlog", "story_points": 3},
            {"id": "db-2", "title": "Create orders table migration", "status": "backlog", "story_points": 2},
            {"id": "db-3", "title": "Create payments table migration", "status": "backlog", "story_points": 2},
            
            # Milestone 2: API
            {"id": "api-1", "title": "Implement cart API", "status": "backlog", "story_points": 5},
            {"id": "api-2", "title": "Implement checkout API", "status": "backlog", "story_points": 8},
            {"id": "api-3", "title": "Implement payment webhook", "status": "backlog", "story_points": 5},
            
            # Milestone 3: Frontend
            {"id": "fe-1", "title": "Build cart component", "status": "backlog", "story_points": 5},
            {"id": "fe-2", "title": "Build checkout form", "status": "backlog", "story_points": 8},
            {"id": "fe-3", "title": "Build order confirmation", "status": "backlog", "story_points": 3},
            
            # Milestone 4: Testing
            {"id": "test-1", "title": "Write checkout E2E tests", "status": "backlog", "story_points": 5},
        ]
        
        # Dependencies as would be recorded by add_dependency tool
        dependencies = [
            # DB schema first
            {"task_id": "db-2", "depends_on": "db-1"},
            {"task_id": "db-3", "depends_on": "db-1"},
            
            # API depends on DB
            {"task_id": "api-1", "depends_on": "db-2"},
            {"task_id": "api-2", "depends_on": "db-2"},
            {"task_id": "api-2", "depends_on": "db-3"},
            {"task_id": "api-3", "depends_on": "db-3"},
            
            # Frontend depends on API
            {"task_id": "fe-1", "depends_on": "api-1"},
            {"task_id": "fe-2", "depends_on": "api-2"},
            {"task_id": "fe-3", "depends_on": "fe-2"},
            
            # Tests depend on frontend
            {"task_id": "test-1", "depends_on": "fe-1"},
            {"task_id": "test-1", "depends_on": "fe-2"},
            {"task_id": "test-1", "depends_on": "fe-3"},
        ]
        
        # Get ordered tasks
        ordered = get_ordered_tasks(tasks, dependencies)
        task_ids = [t["id"] for t in ordered]
        
        # Verify order constraints
        # DB schema must come first
        assert task_ids.index("db-1") < task_ids.index("db-2")
        assert task_ids.index("db-1") < task_ids.index("db-3")
        
        # API after DB
        assert task_ids.index("db-2") < task_ids.index("api-1")
        assert task_ids.index("db-2") < task_ids.index("api-2")
        assert task_ids.index("db-3") < task_ids.index("api-3")
        
        # Frontend after API
        assert task_ids.index("api-1") < task_ids.index("fe-1")
        assert task_ids.index("api-2") < task_ids.index("fe-2")
        
        # Tests last
        assert task_ids.index("fe-1") < task_ids.index("test-1")
        assert task_ids.index("fe-2") < task_ids.index("test-1")
        assert task_ids.index("fe-3") < task_ids.index("test-1")

    @pytest.mark.e2e
    def test_ready_tasks_filter_during_development(self):
        """
        Simulate mid-project development - some tasks done, some blocked.
        
        Developer should only see ready tasks (dependencies satisfied).
        """
        tasks = [
            {"id": "auth-1", "title": "Setup auth module", "status": "done", "story_points": 5},
            {"id": "auth-2", "title": "Implement JWT tokens", "status": "done", "story_points": 3},
            {"id": "auth-3", "title": "Add password reset", "status": "backlog", "story_points": 3},
            {"id": "api-1", "title": "Protected routes middleware", "status": "in_progress", "story_points": 3},
            {"id": "api-2", "title": "User profile endpoint", "status": "backlog", "story_points": 2},
            {"id": "api-3", "title": "Admin endpoints", "status": "backlog", "story_points": 5},
        ]
        
        dependencies = [
            {"task_id": "auth-2", "depends_on": "auth-1"},
            {"task_id": "auth-3", "depends_on": "auth-2"},
            {"task_id": "api-1", "depends_on": "auth-2"},
            {"task_id": "api-2", "depends_on": "api-1"},
            {"task_id": "api-3", "depends_on": "api-1"},
        ]
        
        # Get only ready tasks
        ready = get_ordered_tasks(tasks, dependencies, ready_only=True)
        ready_ids = [t["id"] for t in ready]
        
        # auth-1, auth-2 are done (not returned)
        # api-1 is in progress (not returned)
        # api-2, api-3 are blocked by api-1 (not returned)
        # auth-3 is ready (auth-2 is done)
        assert ready_ids == ["auth-3"]

    @pytest.mark.e2e
    def test_execution_plan_phases(self):
        """
        Test that execution plan correctly groups parallel work.
        
        Phase 0: No dependencies - can be done in parallel
        Phase 1: Depends on phase 0
        etc.
        """
        tasks = [
            {"id": "setup-1", "title": "Project scaffolding", "status": "backlog"},
            {"id": "setup-2", "title": "CI/CD pipeline", "status": "backlog"},
            {"id": "feature-1", "title": "Feature A", "status": "backlog"},
            {"id": "feature-2", "title": "Feature B", "status": "backlog"},
            {"id": "integration", "title": "Integrate A + B", "status": "backlog"},
        ]
        
        dependencies = [
            {"task_id": "feature-1", "depends_on": "setup-1"},
            {"task_id": "feature-2", "depends_on": "setup-1"},
            {"task_id": "integration", "depends_on": "feature-1"},
            {"task_id": "integration", "depends_on": "feature-2"},
        ]
        
        graph = build_dependency_graph(tasks, dependencies)
        plan = graph.get_execution_plan()
        
        # Phase 0: setup-1, setup-2 (no deps)
        phase0_ids = {t["id"] for t in plan[0]["tasks"]}
        assert "setup-1" in phase0_ids
        assert "setup-2" in phase0_ids
        
        # Phase 1: feature-1, feature-2 (both depend only on setup-1)
        phase1_ids = {t["id"] for t in plan[1]["tasks"]}
        assert "feature-1" in phase1_ids
        assert "feature-2" in phase1_ids
        
        # Phase 2: integration (depends on both features)
        phase2_ids = {t["id"] for t in plan[2]["tasks"]}
        assert "integration" in phase2_ids

    @pytest.mark.e2e
    def test_handles_circular_dependency_gracefully(self):
        """
        Circular dependencies should not crash - return fallback order.
        
        This could happen if PlanningAgent makes a mistake.
        """
        tasks = [
            {"id": "task-a", "title": "Task A", "status": "backlog"},
            {"id": "task-b", "title": "Task B", "status": "backlog"},
            {"id": "task-c", "title": "Task C", "status": "backlog"},
        ]
        
        # Circular: A -> B -> C -> A
        dependencies = [
            {"task_id": "task-a", "depends_on": "task-c"},
            {"task_id": "task-b", "depends_on": "task-a"},
            {"task_id": "task-c", "depends_on": "task-b"},
        ]
        
        # Should not raise, returns fallback order
        ordered = get_ordered_tasks(tasks, dependencies)
        assert len(ordered) == 3
        
        # Cycle detection should work
        graph = build_dependency_graph(tasks, dependencies)
        cycle = graph.detect_cycle()
        assert cycle is not None
        assert len(cycle) >= 2

    @pytest.mark.e2e
    def test_milestone_ordering_with_dependencies(self):
        """
        Milestones provide secondary ordering when dependencies are equal.
        """
        tasks = [
            {"id": "m3-task", "title": "M3 Task", "status": "backlog"},
            {"id": "m1-task", "title": "M1 Task", "status": "backlog"},
            {"id": "m2-task", "title": "M2 Task", "status": "backlog"},
        ]
        
        milestones = [
            {"order": 3, "task_ids": ["m3-task"]},
            {"order": 1, "task_ids": ["m1-task"]},
            {"order": 2, "task_ids": ["m2-task"]},
        ]
        
        # No dependencies, so should order by milestone
        ordered = get_ordered_tasks(tasks, [], milestones)
        task_ids = [t["id"] for t in ordered]
        
        assert task_ids == ["m1-task", "m2-task", "m3-task"]

    @pytest.mark.e2e
    def test_story_points_ordering_for_prioritization(self):
        """
        Smaller tasks first when no other ordering factors.
        
        This helps unblock more work faster.
        """
        tasks = [
            {"id": "big", "title": "Big task", "status": "backlog", "story_points": 13},
            {"id": "small", "title": "Small task", "status": "backlog", "story_points": 1},
            {"id": "medium", "title": "Medium task", "status": "backlog", "story_points": 5},
        ]
        
        ordered = get_ordered_tasks(tasks, [])
        task_ids = [t["id"] for t in ordered]
        
        # Smaller tasks should come first
        assert task_ids == ["small", "medium", "big"]

    @pytest.mark.e2e
    def test_blocked_tasks_show_blockers(self):
        """
        When tasks are blocked, show what's blocking them.
        
        Useful for developer visibility.
        """
        tasks = [
            {"id": "blocker-1", "title": "First blocker", "status": "backlog"},
            {"id": "blocker-2", "title": "Second blocker", "status": "backlog"},
            {"id": "blocked", "title": "Blocked task", "status": "backlog"},
        ]
        
        dependencies = [
            {"task_id": "blocked", "depends_on": "blocker-1"},
            {"task_id": "blocked", "depends_on": "blocker-2"},
        ]
        
        graph = build_dependency_graph(tasks, dependencies)
        graph.update_readiness()
        blocked = graph.get_blocked_tasks()
        
        assert len(blocked) == 1
        task, blockers = blocked[0]
        assert task.id == "blocked"
        assert set(blockers) == {"blocker-1", "blocker-2"}

    @pytest.mark.e2e
    def test_complex_multi_milestone_project(self):
        """
        Full complexity test with milestones, dependencies, and mixed statuses.
        
        Simulates a real project mid-development.
        """
        tasks = [
            # Milestone 1: Setup (all done)
            {"id": "setup-1", "title": "Init repo", "status": "done", "story_points": 1},
            {"id": "setup-2", "title": "Add CI", "status": "done", "story_points": 2},
            
            # Milestone 2: Core (mixed)
            {"id": "core-1", "title": "Database models", "status": "done", "story_points": 5},
            {"id": "core-2", "title": "Core business logic", "status": "in_progress", "story_points": 8},
            {"id": "core-3", "title": "Validation layer", "status": "backlog", "story_points": 3},
            
            # Milestone 3: API (blocked)
            {"id": "api-1", "title": "REST endpoints", "status": "backlog", "story_points": 5},
            {"id": "api-2", "title": "GraphQL layer", "status": "backlog", "story_points": 8},
            
            # Milestone 4: Frontend (blocked)
            {"id": "fe-1", "title": "UI components", "status": "backlog", "story_points": 8},
        ]
        
        dependencies = [
            {"task_id": "core-1", "depends_on": "setup-1"},
            {"task_id": "core-2", "depends_on": "core-1"},
            {"task_id": "core-3", "depends_on": "core-1"},
            {"task_id": "api-1", "depends_on": "core-2"},
            {"task_id": "api-1", "depends_on": "core-3"},
            {"task_id": "api-2", "depends_on": "api-1"},
            {"task_id": "fe-1", "depends_on": "api-1"},
        ]
        
        milestones = [
            {"order": 1, "task_ids": ["setup-1", "setup-2"]},
            {"order": 2, "task_ids": ["core-1", "core-2", "core-3"]},
            {"order": 3, "task_ids": ["api-1", "api-2"]},
            {"order": 4, "task_ids": ["fe-1"]},
        ]
        
        graph = build_dependency_graph(tasks, dependencies, milestones)
        graph.update_readiness()
        
        # Check readiness states
        assert graph.nodes["setup-1"].readiness == TaskReadiness.COMPLETE
        assert graph.nodes["setup-2"].readiness == TaskReadiness.COMPLETE
        assert graph.nodes["core-1"].readiness == TaskReadiness.COMPLETE
        assert graph.nodes["core-2"].readiness == TaskReadiness.IN_PROGRESS
        assert graph.nodes["core-3"].readiness == TaskReadiness.READY  # core-1 done
        assert graph.nodes["api-1"].readiness == TaskReadiness.BLOCKED  # waiting on core-2, core-3
        assert graph.nodes["api-2"].readiness == TaskReadiness.BLOCKED  # waiting on api-1
        assert graph.nodes["fe-1"].readiness == TaskReadiness.BLOCKED  # waiting on api-1
        
        # Ready tasks should only be core-3
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "core-3"
        
        # Blocked tasks
        blocked = graph.get_blocked_tasks()
        blocked_ids = {t.id for t, _ in blocked}
        assert blocked_ids == {"api-1", "api-2", "fe-1"}
