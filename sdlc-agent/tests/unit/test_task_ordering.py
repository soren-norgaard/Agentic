# =============================================================================
# Unit Tests for Task Ordering Service
# =============================================================================
# Tests topological sorting, dependency detection, and ready-task filtering.
# =============================================================================

import sys
from pathlib import Path
import importlib.util

import pytest

# Load task_ordering module directly to avoid heavy services/__init__.py dependencies
_task_ordering_path = Path(__file__).parent.parent.parent / "src/sdlc_agent/services/task_ordering.py"
_spec = importlib.util.spec_from_file_location("task_ordering", _task_ordering_path)
_task_ordering = importlib.util.module_from_spec(_spec)
sys.modules["task_ordering"] = _task_ordering
_spec.loader.exec_module(_task_ordering)

DependencyGraph = _task_ordering.DependencyGraph
TaskNode = _task_ordering.TaskNode
TaskReadiness = _task_ordering.TaskReadiness
build_dependency_graph = _task_ordering.build_dependency_graph
get_ordered_tasks = _task_ordering.get_ordered_tasks


class TestTaskNode:
    """Tests for TaskNode dataclass."""

    def test_is_complete_done(self):
        """Task with 'done' status is complete."""
        node = TaskNode(id="1", title="Test", status="done")
        assert node.is_complete() is True

    def test_is_complete_complete(self):
        """Task with 'complete' status is complete."""
        node = TaskNode(id="1", title="Test", status="complete")
        assert node.is_complete() is True

    def test_is_complete_closed(self):
        """Task with 'closed' status is complete."""
        node = TaskNode(id="1", title="Test", status="closed")
        assert node.is_complete() is True

    def test_is_complete_backlog(self):
        """Task with 'backlog' status is not complete."""
        node = TaskNode(id="1", title="Test", status="backlog")
        assert node.is_complete() is False

    def test_is_in_progress(self):
        """Task with 'in_progress' status is in progress."""
        node = TaskNode(id="1", title="Test", status="in_progress")
        assert node.is_in_progress() is True

    def test_is_in_progress_in_review(self):
        """Task with 'in_review' status is in progress."""
        node = TaskNode(id="1", title="Test", status="in_review")
        assert node.is_in_progress() is True

    def test_is_not_in_progress_backlog(self):
        """Task with 'backlog' status is not in progress."""
        node = TaskNode(id="1", title="Test", status="backlog")
        assert node.is_in_progress() is False


class TestDependencyGraph:
    """Tests for DependencyGraph class."""

    def test_add_task(self):
        """Can add a task to the graph."""
        graph = DependencyGraph()
        node = graph.add_task("task-1", "First Task", story_points=3)
        
        assert "task-1" in graph.nodes
        assert node.title == "First Task"
        assert node.story_points == 3

    def test_add_dependency(self):
        """Can add dependencies between tasks."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First Task")
        graph.add_task("task-2", "Second Task")
        
        result = graph.add_dependency("task-2", "task-1")
        
        assert result is True
        assert "task-1" in graph.nodes["task-2"].depends_on
        assert "task-2" in graph.nodes["task-1"].blocks

    def test_add_dependency_missing_task(self):
        """Adding dependency with missing task returns False."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First Task")
        
        result = graph.add_dependency("task-2", "task-1")
        
        assert result is False

    def test_detect_no_cycle(self):
        """Linear dependency chain has no cycle."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First")
        graph.add_task("task-2", "Second")
        graph.add_task("task-3", "Third")
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-2")
        
        cycle = graph.detect_cycle()
        
        assert cycle is None

    def test_detect_simple_cycle(self):
        """Detects simple A -> B -> A cycle."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First")
        graph.add_task("task-2", "Second")
        graph.add_dependency("task-1", "task-2")
        graph.add_dependency("task-2", "task-1")
        
        cycle = graph.detect_cycle()
        
        assert cycle is not None
        assert len(cycle) >= 2

    def test_detect_longer_cycle(self):
        """Detects A -> B -> C -> A cycle."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First")
        graph.add_task("task-2", "Second")
        graph.add_task("task-3", "Third")
        graph.add_dependency("task-1", "task-3")
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-2")
        
        cycle = graph.detect_cycle()
        
        assert cycle is not None

    def test_topological_sort_linear(self):
        """Linear dependencies are sorted correctly."""
        graph = DependencyGraph()
        graph.add_task("task-3", "Third")
        graph.add_task("task-1", "First")
        graph.add_task("task-2", "Second")
        graph.add_dependency("task-2", "task-1")
        graph.add_dependency("task-3", "task-2")
        
        order = graph.topological_sort()
        
        # task-1 must come before task-2, task-2 before task-3
        assert order.index("task-1") < order.index("task-2")
        assert order.index("task-2") < order.index("task-3")

    def test_topological_sort_diamond(self):
        """Diamond pattern sorted correctly."""
        graph = DependencyGraph()
        graph.add_task("base", "Base")
        graph.add_task("left", "Left")
        graph.add_task("right", "Right")
        graph.add_task("top", "Top")
        graph.add_dependency("left", "base")
        graph.add_dependency("right", "base")
        graph.add_dependency("top", "left")
        graph.add_dependency("top", "right")
        
        order = graph.topological_sort()
        
        assert order.index("base") < order.index("left")
        assert order.index("base") < order.index("right")
        assert order.index("left") < order.index("top")
        assert order.index("right") < order.index("top")

    def test_topological_sort_raises_on_cycle(self):
        """Topological sort raises ValueError on cycle."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First")
        graph.add_task("task-2", "Second")
        graph.add_dependency("task-1", "task-2")
        graph.add_dependency("task-2", "task-1")
        
        with pytest.raises(ValueError, match="cycle detected"):
            graph.topological_sort()

    def test_topological_sort_by_milestone(self):
        """Tasks without dependencies ordered by milestone."""
        graph = DependencyGraph()
        graph.add_task("task-b", "Task B", milestone_order=2)
        graph.add_task("task-a", "Task A", milestone_order=1)
        graph.add_task("task-c", "Task C", milestone_order=3)
        
        order = graph.topological_sort()
        
        assert order == ["task-a", "task-b", "task-c"]

    def test_topological_sort_by_story_points(self):
        """Tasks in same milestone ordered by story points."""
        graph = DependencyGraph()
        graph.add_task("big", "Big Task", story_points=8, milestone_order=1)
        graph.add_task("small", "Small Task", story_points=1, milestone_order=1)
        graph.add_task("medium", "Medium Task", story_points=3, milestone_order=1)
        
        order = graph.topological_sort()
        
        # Smaller tasks first
        assert order == ["small", "medium", "big"]

    def test_update_readiness_complete(self):
        """Completed tasks are marked COMPLETE."""
        graph = DependencyGraph()
        graph.add_task("task-1", "Done Task", status="done")
        
        graph.update_readiness()
        
        assert graph.nodes["task-1"].readiness == TaskReadiness.COMPLETE

    def test_update_readiness_in_progress(self):
        """In-progress tasks are marked IN_PROGRESS."""
        graph = DependencyGraph()
        graph.add_task("task-1", "WIP Task", status="in_progress")
        
        graph.update_readiness()
        
        assert graph.nodes["task-1"].readiness == TaskReadiness.IN_PROGRESS

    def test_update_readiness_ready_no_deps(self):
        """Tasks with no dependencies are READY."""
        graph = DependencyGraph()
        graph.add_task("task-1", "Independent Task", status="backlog")
        
        graph.update_readiness()
        
        assert graph.nodes["task-1"].readiness == TaskReadiness.READY

    def test_update_readiness_blocked(self):
        """Tasks with incomplete dependencies are BLOCKED."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First", status="backlog")
        graph.add_task("task-2", "Second", status="backlog")
        graph.add_dependency("task-2", "task-1")
        
        graph.update_readiness()
        
        assert graph.nodes["task-1"].readiness == TaskReadiness.READY
        assert graph.nodes["task-2"].readiness == TaskReadiness.BLOCKED

    def test_update_readiness_unblocked(self):
        """Tasks become READY when dependencies complete."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First", status="done")
        graph.add_task("task-2", "Second", status="backlog")
        graph.add_dependency("task-2", "task-1")
        
        graph.update_readiness()
        
        assert graph.nodes["task-2"].readiness == TaskReadiness.READY

    def test_get_ready_tasks(self):
        """Returns only ready tasks in order."""
        graph = DependencyGraph()
        graph.add_task("task-1", "First", status="backlog")
        graph.add_task("task-2", "Second", status="backlog")
        graph.add_task("task-3", "Third", status="done")
        graph.add_dependency("task-2", "task-1")
        
        ready = graph.get_ready_tasks()
        
        # task-1 is ready (no deps), task-2 is blocked, task-3 is complete
        assert len(ready) == 1
        assert ready[0].id == "task-1"

    def test_get_blocked_tasks(self):
        """Returns blocked tasks with their blockers."""
        graph = DependencyGraph()
        graph.add_task("blocker", "Blocker", status="backlog")
        graph.add_task("blocked", "Blocked", status="backlog")
        graph.add_dependency("blocked", "blocker")
        
        blocked = graph.get_blocked_tasks()
        
        assert len(blocked) == 1
        task, blockers = blocked[0]
        assert task.id == "blocked"
        assert "blocker" in blockers

    def test_get_execution_plan(self):
        """Returns phased execution plan."""
        graph = DependencyGraph()
        graph.add_task("phase0-a", "Phase 0 A", status="backlog")
        graph.add_task("phase0-b", "Phase 0 B", status="backlog")
        graph.add_task("phase1", "Phase 1", status="backlog")
        graph.add_dependency("phase1", "phase0-a")
        graph.add_dependency("phase1", "phase0-b")
        
        plan = graph.get_execution_plan()
        
        assert len(plan) == 2
        phase0_ids = [t["id"] for t in plan[0]["tasks"]]
        phase1_ids = [t["id"] for t in plan[1]["tasks"]]
        assert "phase0-a" in phase0_ids
        assert "phase0-b" in phase0_ids
        assert "phase1" in phase1_ids


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph function."""

    def test_empty_inputs(self):
        """Empty tasks and dependencies returns empty graph."""
        graph = build_dependency_graph([], [])
        assert len(graph.nodes) == 0

    def test_tasks_only(self):
        """Tasks without dependencies are added."""
        tasks = [
            {"id": "task-1", "title": "First", "story_points": 3, "status": "backlog"},
            {"id": "task-2", "title": "Second", "story_points": 5, "status": "done"},
        ]
        
        graph = build_dependency_graph(tasks, [])
        
        assert len(graph.nodes) == 2
        assert graph.nodes["task-1"].story_points == 3
        assert graph.nodes["task-2"].status == "done"

    def test_with_dependencies(self):
        """Dependencies are correctly linked."""
        tasks = [
            {"id": "task-1", "title": "First"},
            {"id": "task-2", "title": "Second"},
        ]
        dependencies = [
            {"task_id": "task-2", "depends_on": "task-1", "type": "blocks"},
        ]
        
        graph = build_dependency_graph(tasks, dependencies)
        
        assert "task-1" in graph.nodes["task-2"].depends_on

    def test_with_milestones(self):
        """Milestone order is applied to tasks."""
        tasks = [
            {"id": "task-1", "title": "First"},
            {"id": "task-2", "title": "Second"},
        ]
        milestones = [
            {"order": 1, "task_ids": ["task-1"]},
            {"order": 2, "task_ids": ["task-2"]},
        ]
        
        graph = build_dependency_graph(tasks, [], milestones)
        
        assert graph.nodes["task-1"].milestone_order == 1
        assert graph.nodes["task-2"].milestone_order == 2


class TestGetOrderedTasks:
    """Tests for get_ordered_tasks function."""

    def test_returns_sorted_list(self):
        """Returns task dicts in dependency order."""
        tasks = [
            {"id": "task-2", "title": "Second"},
            {"id": "task-1", "title": "First"},
        ]
        dependencies = [
            {"task_id": "task-2", "depends_on": "task-1"},
        ]
        
        ordered = get_ordered_tasks(tasks, dependencies)
        
        assert ordered[0]["id"] == "task-1"
        assert ordered[1]["id"] == "task-2"

    def test_handles_cycle(self):
        """Returns tasks in fallback order on cycle."""
        tasks = [
            {"id": "task-1", "title": "First"},
            {"id": "task-2", "title": "Second"},
        ]
        dependencies = [
            {"task_id": "task-1", "depends_on": "task-2"},
            {"task_id": "task-2", "depends_on": "task-1"},
        ]
        
        # Should not raise, returns fallback order
        ordered = get_ordered_tasks(tasks, dependencies)
        assert len(ordered) == 2


class TestGetReadyToDevelop:
    """Tests for get_ordered_tasks with ready_only=True."""

    def test_filters_blocked(self):
        """Only returns tasks that are ready."""
        tasks = [
            {"id": "ready", "title": "Ready", "status": "backlog"},
            {"id": "blocked", "title": "Blocked", "status": "backlog"},
        ]
        dependencies = [
            {"task_id": "blocked", "depends_on": "ready"},
        ]
        
        ready = get_ordered_tasks(tasks, dependencies, ready_only=True)
        
        assert len(ready) == 1
        assert ready[0]["id"] == "ready"

    def test_unblocks_when_complete(self):
        """Task becomes ready when dependency is complete."""
        tasks = [
            {"id": "done", "title": "Done", "status": "done"},
            {"id": "waiting", "title": "Waiting", "status": "backlog"},
        ]
        dependencies = [
            {"task_id": "waiting", "depends_on": "done"},
        ]
        
        ready = get_ordered_tasks(tasks, dependencies, ready_only=True)
        
        assert len(ready) == 1
        assert ready[0]["id"] == "waiting"

    def test_excludes_complete_and_in_progress(self):
        """Completed and in-progress tasks are not returned."""
        tasks = [
            {"id": "done", "title": "Done", "status": "done"},
            {"id": "wip", "title": "WIP", "status": "in_progress"},
            {"id": "ready", "title": "Ready", "status": "backlog"},
        ]
        
        ready = get_ordered_tasks(tasks, [], ready_only=True)
        
        assert len(ready) == 1
        assert ready[0]["id"] == "ready"

    def test_respects_milestone_order(self):
        """Tasks are ordered by milestone."""
        tasks = [
            {"id": "later", "title": "Later", "status": "backlog"},
            {"id": "first", "title": "First", "status": "backlog"},
        ]
        milestones = [
            {"order": 2, "task_ids": ["later"]},
            {"order": 1, "task_ids": ["first"]},
        ]
        
        ready = get_ordered_tasks(tasks, [], milestones, ready_only=True)
        
        assert ready[0]["id"] == "first"
        assert ready[1]["id"] == "later"
