# =============================================================================
# SDLC Agent - Task Ordering Service
# =============================================================================
# Provides topological sorting and dependency-aware task ordering.
# Ensures developers work on tasks in the correct sequence.
# =============================================================================

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskReadiness(str, Enum):
    """Task readiness status based on dependencies."""
    
    READY = "ready"  # All dependencies complete, can be worked on
    BLOCKED = "blocked"  # Waiting on incomplete dependencies
    IN_PROGRESS = "in_progress"  # Currently being worked on
    COMPLETE = "complete"  # Task is done


@dataclass
class TaskNode:
    """Represents a task in the dependency graph."""
    
    id: str
    title: str
    story_points: int = 0
    status: str = "backlog"
    milestone_order: int = 999  # Higher = later milestone
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)  # Tasks this blocks
    readiness: TaskReadiness = TaskReadiness.BLOCKED
    
    def is_complete(self) -> bool:
        """Check if task is in a completed state."""
        return self.status in ("done", "complete", "closed")
    
    def is_in_progress(self) -> bool:
        """Check if task is currently being worked on."""
        return self.status in ("in_progress", "in_review")


@dataclass
class DependencyGraph:
    """
    Dependency graph for tasks with topological sorting.
    
    Supports:
    - Topological sort for execution order
    - Cycle detection
    - Ready-to-work task identification
    - Milestone-aware ordering
    """
    
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    
    def add_task(
        self,
        task_id: str,
        title: str,
        story_points: int = 0,
        status: str = "backlog",
        milestone_order: int = 999,
    ) -> TaskNode:
        """Add a task to the graph."""
        node = TaskNode(
            id=task_id,
            title=title,
            story_points=story_points,
            status=status,
            milestone_order=milestone_order,
        )
        self.nodes[task_id] = node
        return node
    
    def add_dependency(
        self,
        task_id: str,
        depends_on_id: str,
    ) -> bool:
        """
        Add a dependency: task_id depends on depends_on_id.
        
        Returns False if either task doesn't exist.
        """
        if task_id not in self.nodes or depends_on_id not in self.nodes:
            return False
        
        self.nodes[task_id].depends_on.append(depends_on_id)
        self.nodes[depends_on_id].blocks.append(task_id)
        return True
    
    def detect_cycle(self) -> list[str] | None:
        """
        Detect if there's a cycle in the dependency graph.
        
        Returns the cycle path if found, None otherwise.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self.nodes}
        parent = {}
        
        def dfs(node_id: str) -> list[str] | None:
            color[node_id] = GRAY
            
            for dep_id in self.nodes[node_id].depends_on:
                if dep_id not in self.nodes:
                    continue
                    
                if color[dep_id] == GRAY:
                    # Found cycle - reconstruct path
                    cycle = [dep_id, node_id]
                    current = node_id
                    while current in parent and parent[current] != dep_id:
                        current = parent[current]
                        cycle.append(current)
                    return cycle
                
                if color[dep_id] == WHITE:
                    parent[dep_id] = node_id
                    result = dfs(dep_id)
                    if result:
                        return result
            
            color[node_id] = BLACK
            return None
        
        for node_id in self.nodes:
            if color[node_id] == WHITE:
                cycle = dfs(node_id)
                if cycle:
                    return cycle
        
        return None
    
    def topological_sort(self) -> list[str]:
        """
        Return tasks in topological order (dependencies first).
        
        Uses Kahn's algorithm for stable, deterministic ordering.
        Within the same dependency level, orders by:
        1. Milestone order (earlier milestones first)
        2. Story points (smaller tasks first)
        3. Title (alphabetical, for stability)
        
        Raises ValueError if graph has cycles.
        """
        cycle = self.detect_cycle()
        if cycle:
            raise ValueError(f"Dependency cycle detected: {' -> '.join(cycle)}")
        
        # Calculate in-degree for each node
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node in self.nodes.values():
            for dep_id in node.depends_on:
                if dep_id in self.nodes:
                    in_degree[node.id] += 1
        
        # Start with nodes that have no dependencies
        # Sort by milestone, story points, then title for deterministic order
        def sort_key(node_id: str) -> tuple:
            node = self.nodes[node_id]
            return (node.milestone_order, node.story_points, node.title)
        
        queue = deque(
            sorted(
                [nid for nid, deg in in_degree.items() if deg == 0],
                key=sort_key
            )
        )
        
        result = []
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            # Find all tasks that this task blocks
            blocked_tasks = []
            for other_id, other_node in self.nodes.items():
                if node_id in other_node.depends_on:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        blocked_tasks.append(other_id)
            
            # Add newly unblocked tasks in sorted order
            blocked_tasks.sort(key=sort_key)
            queue.extend(blocked_tasks)
        
        return result
    
    def update_readiness(self) -> None:
        """Update the readiness status of all tasks based on dependencies."""
        for node in self.nodes.values():
            if node.is_complete():
                node.readiness = TaskReadiness.COMPLETE
            elif node.is_in_progress():
                node.readiness = TaskReadiness.IN_PROGRESS
            else:
                # Check if all dependencies are complete
                all_deps_complete = all(
                    self.nodes.get(dep_id, TaskNode(id=dep_id, title="")).is_complete()
                    for dep_id in node.depends_on
                    if dep_id in self.nodes
                )
                node.readiness = TaskReadiness.READY if all_deps_complete else TaskReadiness.BLOCKED
    
    def get_ready_tasks(self) -> list[TaskNode]:
        """
        Get all tasks that are ready to be worked on.
        
        A task is ready if:
        1. It's not complete or in progress
        2. All its dependencies are complete
        
        Returns tasks in recommended execution order.
        """
        self.update_readiness()
        
        # Get topological order
        try:
            ordered_ids = self.topological_sort()
        except ValueError:
            # If there's a cycle, just return by milestone/points
            ordered_ids = sorted(
                self.nodes.keys(),
                key=lambda nid: (
                    self.nodes[nid].milestone_order,
                    self.nodes[nid].story_points,
                    self.nodes[nid].title,
                ),
            )
        
        ready = []
        for node_id in ordered_ids:
            node = self.nodes[node_id]
            if node.readiness == TaskReadiness.READY:
                ready.append(node)
        
        return ready
    
    def get_blocked_tasks(self) -> list[tuple[TaskNode, list[str]]]:
        """
        Get all blocked tasks with their blocking dependencies.
        
        Returns list of (task, blocking_task_ids).
        """
        self.update_readiness()
        
        blocked = []
        for node in self.nodes.values():
            if node.readiness == TaskReadiness.BLOCKED:
                blocking = [
                    dep_id for dep_id in node.depends_on
                    if dep_id in self.nodes and not self.nodes[dep_id].is_complete()
                ]
                blocked.append((node, blocking))
        
        return blocked
    
    def get_execution_plan(self) -> list[dict[str, Any]]:
        """
        Get a complete execution plan with phases.
        
        Returns a list of phases, each containing tasks that can be 
        worked on in parallel within that phase.
        """
        self.update_readiness()
        
        # Build phases based on dependency depth
        depth = {node_id: 0 for node_id in self.nodes}
        
        # BFS to calculate depth
        changed = True
        while changed:
            changed = False
            for node_id, node in self.nodes.items():
                for dep_id in node.depends_on:
                    if dep_id in depth:
                        new_depth = depth[dep_id] + 1
                        if new_depth > depth[node_id]:
                            depth[node_id] = new_depth
                            changed = True
        
        # Group by depth
        phases: dict[int, list[TaskNode]] = defaultdict(list)
        for node_id, d in depth.items():
            phases[d].append(self.nodes[node_id])
        
        # Sort tasks within each phase
        result = []
        for phase_num in sorted(phases.keys()):
            phase_tasks = sorted(
                phases[phase_num],
                key=lambda n: (n.milestone_order, n.story_points, n.title),
            )
            result.append({
                "phase": phase_num + 1,
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "story_points": t.story_points,
                        "status": t.status,
                        "readiness": t.readiness.value,
                        "depends_on": t.depends_on,
                    }
                    for t in phase_tasks
                ],
                "total_points": sum(t.story_points for t in phase_tasks),
            })
        
        return result


def build_dependency_graph(
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    milestones: list[dict[str, Any]] | None = None,
) -> DependencyGraph:
    """
    Build a dependency graph from planning agent output.
    
    Args:
        tasks: List of task dicts with id, title, story_points, status
        dependencies: List of dependency dicts with task_id, depends_on
        milestones: Optional list of milestone dicts with task_ids, order
    
    Returns:
        Populated DependencyGraph
    """
    graph = DependencyGraph()
    
    # Build milestone lookup
    task_to_milestone: dict[str, int] = {}
    if milestones:
        for milestone in milestones:
            order = milestone.get("order", 999)
            for task_id in milestone.get("task_ids", []):
                task_to_milestone[task_id] = order
    
    # Add tasks
    for task in tasks:
        task_id = task.get("id", "")
        if not task_id:
            continue
        
        graph.add_task(
            task_id=task_id,
            title=task.get("title", "Untitled"),
            story_points=task.get("story_points", 0),
            status=task.get("status", "backlog"),
            milestone_order=task_to_milestone.get(task_id, 999),
        )
    
    # Add dependencies
    for dep in dependencies:
        task_id = dep.get("task_id", "")
        depends_on = dep.get("depends_on", "")
        if task_id and depends_on:
            graph.add_dependency(task_id, depends_on)
    
    return graph


def get_ordered_tasks(
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    milestones: list[dict[str, Any]] | None = None,
    ready_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Get tasks in dependency-aware execution order.
    
    Args:
        tasks: List of task dicts
        dependencies: List of dependency dicts  
        milestones: Optional milestones for ordering
        ready_only: If True, only return tasks ready for development
    
    Returns:
        Ordered list of tasks with readiness status added
    """
    graph = build_dependency_graph(tasks, dependencies, milestones)
    
    if ready_only:
        ready_nodes = graph.get_ready_tasks()
        return [
            {
                "id": node.id,
                "title": node.title,
                "story_points": node.story_points,
                "status": node.status,
                "readiness": node.readiness.value,
                "depends_on": node.depends_on,
                "blocks": node.blocks,
            }
            for node in ready_nodes
        ]
    
    # Return all tasks in order
    graph.update_readiness()
    try:
        ordered_ids = graph.topological_sort()
    except ValueError:
        ordered_ids = list(graph.nodes.keys())
    
    return [
        {
            "id": graph.nodes[nid].id,
            "title": graph.nodes[nid].title,
            "story_points": graph.nodes[nid].story_points,
            "status": graph.nodes[nid].status,
            "readiness": graph.nodes[nid].readiness.value,
            "depends_on": graph.nodes[nid].depends_on,
            "blocks": graph.nodes[nid].blocks,
        }
        for nid in ordered_ids
        if nid in graph.nodes
    ]
