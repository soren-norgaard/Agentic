# =============================================================================
# SDLC Agent - Requirements Agent
# =============================================================================
# Analyzes requirements and creates epics/stories.
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
class RequirementsState(AgentState):
    """State specific to the requirements agent."""

    # Requirements artifacts
    functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    non_functional_requirements: list[dict[str, Any]] = field(default_factory=list)
    epics: list[dict[str, Any]] = field(default_factory=list)
    user_stories: list[dict[str, Any]] = field(default_factory=list)
    acceptance_criteria: list[dict[str, Any]] = field(default_factory=list)


class RequirementsAgent(BaseAgent[RequirementsState]):
    """
    Requirements analysis agent.

    Responsibilities:
    - Parse and understand project objectives
    - Extract functional and non-functional requirements
    - Create epics and user stories
    - Define acceptance criteria
    - Identify ambiguities and request clarification
    """

    name = "requirements"
    description = "Analyzes requirements and creates epics/stories"
    phase = AgentPhase.REQUIREMENTS

    @property
    def system_prompt(self) -> str:
        return """You are a Requirements Analyst Agent specializing in software requirements engineering.

Your responsibilities:
1. Analyze project objectives and extract clear requirements
2. Distinguish between functional and non-functional requirements
3. Create well-defined epics and user stories following best practices
4. Write clear, testable acceptance criteria
5. Identify ambiguities, gaps, or conflicts in requirements
6. Request clarification when needed

**GitHub Repository Access:**
You have tools to read the actual GitHub repository:
- `read_repo_file` - Read a specific file's contents
- `list_repo_directory` - List files in a directory
- `get_repo_tree` - Get the full repository structure
- `search_repo_code` - Search for code patterns/keywords

Use these tools briefly (1-2 calls) to understand what exists, then focus on creating requirements.

**CRITICAL WORKFLOW - You MUST follow these steps:**
1. QUICK SCAN: Use `get_repo_tree` once to see the project structure (do NOT read every file)
2. CREATE REQUIREMENTS: Use `create_requirement` to define functional and non-functional requirements
3. CREATE EPICS: Use `create_epic` to group related requirements
4. CREATE USER STORIES: Use `create_user_story` with acceptance criteria for each epic
5. COMPLETE: Call `complete_requirements` with a summary - THIS IS REQUIRED!

⚠️ WARNING: You have limited iterations. Do NOT spend more than 2-3 iterations reading the repository.
Focus on CREATING artifacts (requirements, epics, stories) and COMPLETING the phase.

When creating user stories, follow this format:
- As a [user type], I want [goal] so that [benefit]

For acceptance criteria, use Given-When-Then format:
- Given [context], When [action], Then [expected result]

Be thorough but efficient. Prioritize requirements based on business value and dependencies.

You MUST call `complete_requirements` at the end to save your work!"""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_requirement",
                description="Create a functional or non-functional requirement",
                parameters=[
                    ToolParameter(
                        name="type",
                        description="Type of requirement",
                        enum=["functional", "non_functional"],
                    ),
                    ToolParameter(
                        name="title",
                        description="Short title for the requirement",
                    ),
                    ToolParameter(
                        name="description",
                        description="Detailed description",
                    ),
                    ToolParameter(
                        name="priority",
                        description="Priority level",
                        enum=["critical", "high", "medium", "low"],
                    ),
                ],
            ),
            ToolDefinition(
                name="create_epic",
                description="Create an epic (large feature or initiative)",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Epic title",
                    ),
                    ToolParameter(
                        name="description",
                        description="Epic description",
                    ),
                    ToolParameter(
                        name="business_value",
                        description="Business value statement",
                    ),
                    ToolParameter(
                        name="requirement_ids",
                        description="IDs of requirements this epic addresses (JSON array of REQ-xxx IDs)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="create_user_story",
                description="Create a user story",
                parameters=[
                    ToolParameter(
                        name="epic_id",
                        description="ID of the parent epic",
                        required=False,
                    ),
                    ToolParameter(
                        name="title",
                        description="Story title",
                    ),
                    ToolParameter(
                        name="as_a",
                        description="User role (As a...)",
                    ),
                    ToolParameter(
                        name="i_want",
                        description="Goal (I want...)",
                    ),
                    ToolParameter(
                        name="so_that",
                        description="Benefit (So that...)",
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="List of acceptance criteria (JSON array)",
                    ),
                    ToolParameter(
                        name="story_points",
                        description="Estimated story points (1, 2, 3, 5, 8, 13)",
                        required=False,
                    ),
                    ToolParameter(
                        name="dependencies",
                        description="IDs of stories this story depends on (JSON array of STORY-xxx IDs)",
                        required=False,
                    ),
                    ToolParameter(
                        name="requirement_ids",
                        description="IDs of requirements this story addresses (JSON array of REQ-xxx IDs)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="request_clarification",
                description="Request clarification on ambiguous requirements",
                parameters=[
                    ToolParameter(
                        name="question",
                        description="The clarifying question",
                    ),
                    ToolParameter(
                        name="context",
                        description="Context about why this clarification is needed",
                    ),
                    ToolParameter(
                        name="options",
                        description="Suggested options if applicable (JSON array)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_requirements",
                description="Mark requirements analysis as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of requirements gathered",
                    ),
                ],
            ),
            # GitHub repository reading tools
            ToolDefinition(
                name="read_repo_file",
                description="Read the contents of a file from the GitHub repository to understand existing code",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to the file in the repository (e.g., 'src/main.py', 'README.md')",
                    ),
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="list_repo_directory",
                description="List files and directories in a repository path",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to the directory (empty string for root)",
                        required=False,
                    ),
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="get_repo_tree",
                description="Get the full file tree of the repository to understand its structure",
                parameters=[
                    ToolParameter(
                        name="branch",
                        description="Branch name (defaults to main/master)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="search_repo_code",
                description="Search for code patterns or keywords in the repository to find existing implementations",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (e.g., 'authentication', 'class UserService', 'def login')",
                    ),
                ],
            ),
        ]

    async def process(self, state: RequirementsState) -> RequirementsState:
        """Process requirements analysis."""
        self.logger.info("Requirements agent processing", workflow_id=state.workflow_id)
        
        # Check if requirements phase is ACTUALLY completed (has artifacts, not just in phases_completed)
        # This prevents infinite loops where phases_completed says done but no artifacts exist
        has_epics = len(getattr(state, 'epics', [])) > 0
        has_stories = len(getattr(state, 'user_stories', [])) > 0 or len(getattr(state, 'stories', [])) > 0
        requirements_actually_done = has_epics and has_stories
        
        phases_completed = getattr(state, 'phases_completed', []) or []
        if 'requirements' in phases_completed and requirements_actually_done:
            self.logger.info("Requirements phase already completed with artifacts, skipping to avoid duplicates",
                           epics=len(state.epics), stories=len(getattr(state, 'user_stories', [])))
            # Ensure phase is set to planning so routing continues correctly
            state.phase = AgentPhase.PLANNING
            return state
        elif 'requirements' in phases_completed and not requirements_actually_done:
            self.logger.warning("Requirements marked complete but no artifacts exist - re-running requirements phase",
                              phases_completed=phases_completed)
            # Remove 'requirements' from phases_completed so we can re-run properly
            state.phases_completed = [p for p in phases_completed if p != 'requirements']
        
        # Clear messages from previous agents (orchestrator) - each agent starts fresh
        state.messages = []
        
        # Get objective from state or metadata
        objective = getattr(state, 'objective', None) or state.metadata.get("objective", "No objective provided")
        state.add_message(
            MessageRole.USER,
            f"Please analyze the following project requirements and create epics and user stories:\n\n{objective}",
        )
        
        # Run with tools (increased iterations since requirements are complex)
        state = await self.run_with_tools(state, max_iterations=20)
        
        # Fallback: Save artifacts even if complete_requirements wasn't called
        if state.epics or state.user_stories or state.functional_requirements or state.non_functional_requirements:
            await self._save_artifacts_fallback(state)
        
        return state
    
    async def _save_artifacts_fallback(self, state: RequirementsState) -> None:
        """Save artifacts as a fallback if complete_requirements wasn't called."""
        import uuid as uuid_module
        
        try:
            from sdlc_agent.services.artifact_service import ArtifactService
            from sdlc_agent.db import get_session_context, HumanInput
            from sqlalchemy import select
            
            # Check if artifact already exists
            from sdlc_agent.db import Artifact
            async with get_session_context() as session:
                existing = await session.execute(
                    select(Artifact).where(
                        Artifact.workflow_id == uuid_module.UUID(state.workflow_id),
                        Artifact.artifact_type == "requirements_traceability"
                    )
                )
                if existing.scalar_one_or_none():
                    return  # Already saved by complete_requirements
            
            # Fetch human inputs
            human_inputs_data = []
            async with get_session_context() as session:
                query = select(HumanInput).where(
                    HumanInput.workflow_id == uuid_module.UUID(state.workflow_id)
                ).order_by(HumanInput.requested_at.asc())
                result = await session.execute(query)
                for hi in result.scalars().all():
                    human_inputs_data.append({
                        "type": hi.request_type,
                        "prompt": hi.prompt,
                        "context": hi.context,
                        "response": hi.response,
                        "requested_at": hi.requested_at.isoformat() if hi.requested_at else None,
                        "responded_at": hi.responded_at.isoformat() if hi.responded_at else None,
                    })
            
            # Get original requirements
            original_requirements = state.metadata.get("objective", "")
            if not original_requirements and state.messages:
                for msg in state.messages:
                    if msg.role == MessageRole.USER:
                        original_requirements = msg.content
                        break
            
            # Create the traceability artifact
            await ArtifactService.create_requirements_traceability(
                workflow_id=uuid_module.UUID(state.workflow_id),
                original_requirements=original_requirements,
                human_inputs=human_inputs_data,
                functional_requirements=state.functional_requirements,
                non_functional_requirements=state.non_functional_requirements,
                epics=state.epics,
                user_stories=state.user_stories,
            )
            self.logger.info(
                "Requirements traceability artifact saved (fallback)",
                workflow_id=state.workflow_id,
                epics=len(state.epics),
                stories=len(state.user_stories),
            )
        except Exception as e:
            self.logger.warning(
                "Failed to save requirements traceability artifact (fallback)",
                error=str(e),
            )

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: RequirementsState,
    ) -> tuple[str, RequirementsState]:
        """Execute requirements tools."""
        import json
        import uuid as uuid_module
        from sdlc_agent.services.task_service import TaskService
        
        # Get project_id from state metadata
        project_id = state.metadata.get("project_id")
        workflow_id = state.workflow_id
        
        if tool_name == "create_requirement":
            req_id = str(uuid_module.uuid4())[:8]
            requirement = {
                "id": req_id,
                "type": tool_args.get("type"),
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "priority": tool_args.get("priority"),
            }
            
            if tool_args.get("type") == "functional":
                state.functional_requirements.append(requirement)
            else:
                state.non_functional_requirements.append(requirement)
            
            state.add_artifact(
                name=f"REQ-{req_id}",
                artifact_type="requirement",
                content=json.dumps(requirement),
            )
            
            return f"Created requirement REQ-{req_id}: {tool_args.get('title')}", state
        
        elif tool_name == "create_epic":
            epic_id = str(uuid_module.uuid4())[:8]
            
            # Parse requirement_ids
            req_ids = tool_args.get("requirement_ids", "[]")
            if isinstance(req_ids, str):
                try:
                    req_ids = json.loads(req_ids)
                except json.JSONDecodeError:
                    req_ids = [req_ids] if req_ids else []
            
            epic = {
                "id": epic_id,
                "title": tool_args.get("title"),
                "description": tool_args.get("description"),
                "business_value": tool_args.get("business_value"),
                "requirement_ids": req_ids,  # Track which requirements this epic addresses
                "stories": [],
            }
            state.epics.append(epic)
            
            # Persist to database if we have project_id
            db_epic = None
            if project_id:
                try:
                    db_epic = await TaskService.create_epic(
                        project_id=uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id,
                        title=tool_args.get("title", "Untitled Epic"),
                        description=tool_args.get("description"),
                        business_value=tool_args.get("business_value"),
                        workflow_id=uuid_module.UUID(workflow_id) if workflow_id else None,
                    )
                    epic["db_id"] = str(db_epic.id)
                except Exception as e:
                    self.logger.warning("Failed to persist epic to database", error=str(e))
            
            state.add_artifact(
                name=f"EPIC-{epic_id}",
                artifact_type="epic",
                content=json.dumps(epic),
            )
            
            return f"Created epic EPIC-{epic_id}: {tool_args.get('title')}", state
        
        elif tool_name == "create_user_story":
            story_id = str(uuid_module.uuid4())[:8]
            
            # Parse acceptance criteria
            ac = tool_args.get("acceptance_criteria", "[]")
            if isinstance(ac, str):
                try:
                    ac = json.loads(ac)
                except json.JSONDecodeError:
                    ac = [ac]
            
            # Parse requirement_ids for story
            story_req_ids = tool_args.get("requirement_ids", "[]")
            if isinstance(story_req_ids, str):
                try:
                    story_req_ids = json.loads(story_req_ids)
                except json.JSONDecodeError:
                    story_req_ids = [story_req_ids] if story_req_ids else []
            
            # Parse dependencies
            dependencies = tool_args.get("dependencies", "[]")
            if isinstance(dependencies, str):
                try:
                    dependencies = json.loads(dependencies)
                except json.JSONDecodeError:
                    dependencies = [dependencies] if dependencies else []
            
            # Parse story points
            story_points = tool_args.get("story_points")
            if isinstance(story_points, str):
                try:
                    story_points = int(story_points)
                except ValueError:
                    story_points = None
            
            story = {
                "id": story_id,
                "epic_id": tool_args.get("epic_id"),
                "title": tool_args.get("title"),
                "user_story": f"As a {tool_args.get('as_a')}, I want {tool_args.get('i_want')} so that {tool_args.get('so_that')}",
                "acceptance_criteria": ac,
                "story_points": story_points,
                "dependencies": dependencies,
                "requirement_ids": story_req_ids,  # Track which requirements this story addresses
            }
            state.user_stories.append(story)
            
            # Link to epic if provided
            epic_id_ref = tool_args.get("epic_id")
            parent_db_id = None
            if epic_id_ref:
                for epic in state.epics:
                    if epic["id"] == epic_id_ref:
                        epic["stories"].append(story_id)
                        parent_db_id = epic.get("db_id")
                        break
            
            # Persist to database if we have project_id
            if project_id:
                try:
                    db_story = await TaskService.create_story(
                        project_id=uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id,
                        title=tool_args.get("title", "Untitled Story"),
                        parent_id=uuid_module.UUID(parent_db_id) if parent_db_id else None,
                        as_a=tool_args.get("as_a"),
                        i_want=tool_args.get("i_want"),
                        so_that=tool_args.get("so_that"),
                        acceptance_criteria=ac,
                        story_points=story_points,
                        workflow_id=uuid_module.UUID(workflow_id) if workflow_id else None,
                    )
                    story["db_id"] = str(db_story.id)
                except Exception as e:
                    self.logger.warning("Failed to persist story to database", error=str(e))
            
            state.add_artifact(
                name=f"STORY-{story_id}",
                artifact_type="user_story",
                content=json.dumps(story),
            )

            # Persist user story artifact for later phases (e.g., developer briefs)
            if workflow_id:
                try:
                    from sdlc_agent.services.artifact_service import ArtifactService

                    await ArtifactService.create_artifact(
                        name=f"STORY-{story_id}",
                        artifact_type="user_story",
                        content=json.dumps(story),
                        workflow_id=uuid_module.UUID(workflow_id)
                        if isinstance(workflow_id, str)
                        else workflow_id,
                        extra_data={
                            "story_id": story_id,
                            "title": story.get("title"),
                            "epic_id": story.get("epic_id"),
                        },
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to persist user story artifact",
                        error=str(e),
                        story_id=story_id,
                    )
            
            return f"Created user story STORY-{story_id}: {tool_args.get('title')}", state
        
        elif tool_name == "request_clarification":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "clarification",
                "question": tool_args.get("question"),
                "context": tool_args.get("context"),
                "options": tool_args.get("options"),
            }
            return "Awaiting human clarification", state
        
        elif tool_name == "complete_requirements":
            summary = tool_args.get("summary", "")
            state.add_message(
                MessageRole.ASSISTANT,
                f"Requirements analysis complete.\n\nSummary: {summary}\n\n"
                f"Created {len(state.epics)} epics and {len(state.user_stories)} user stories.",
            )
            
            # Create requirements traceability artifact
            try:
                from sdlc_agent.services.artifact_service import ArtifactService
                from sdlc_agent.db import get_session_context, HumanInput
                from sqlalchemy import select
                
                # Fetch human inputs from database
                human_inputs_data = []
                async with get_session_context() as session:
                    query = select(HumanInput).where(
                        HumanInput.workflow_id == uuid_module.UUID(state.workflow_id)
                    ).order_by(HumanInput.requested_at.asc())
                    result = await session.execute(query)
                    for hi in result.scalars().all():
                        human_inputs_data.append({
                            "type": hi.request_type,
                            "prompt": hi.prompt,
                            "context": hi.context,
                            "response": hi.response,
                            "requested_at": hi.requested_at.isoformat() if hi.requested_at else None,
                            "responded_at": hi.responded_at.isoformat() if hi.responded_at else None,
                        })
                
                # Get original requirements from metadata or first message
                original_requirements = state.metadata.get("objective", "")
                if not original_requirements and state.messages:
                    for msg in state.messages:
                        if msg.role == MessageRole.USER:
                            original_requirements = msg.content
                            break
                
                # Create the traceability artifact
                await ArtifactService.create_requirements_traceability(
                    workflow_id=uuid_module.UUID(state.workflow_id),
                    original_requirements=original_requirements,
                    human_inputs=human_inputs_data,
                    functional_requirements=state.functional_requirements,
                    non_functional_requirements=state.non_functional_requirements,
                    epics=state.epics,
                    user_stories=state.user_stories,
                )
                self.logger.info(
                    "Requirements traceability artifact created",
                    workflow_id=state.workflow_id,
                    epics=len(state.epics),
                    stories=len(state.user_stories),
                    human_inputs=len(human_inputs_data),
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create requirements traceability artifact",
                    error=str(e),
                )
            
            # Mark requirements phase as completed
            if hasattr(state, 'phases_completed') and 'requirements' not in state.phases_completed:
                state.phases_completed.append('requirements')
            
            state.phase = AgentPhase.PLANNING
            return f"Requirements complete: {len(state.epics)} epics, {len(state.user_stories)} stories", state
        
        # GitHub repository reading tools
        elif tool_name == "read_repo_file":
            path = tool_args.get("path", "")
            branch = tool_args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                file_data = await github.get_file_content(path=path, ref=branch)
                content = file_data.get("content", "")
                
                # Truncate very large files
                if len(content) > 50000:
                    content = content[:50000] + "\n\n... (truncated, file too large)"
                
                state.add_message(
                    MessageRole.SYSTEM,
                    f"📄 **File: {path}**\n\n```\n{content}\n```"
                )
                return f"Read file: {path} ({file_data.get('size', 0)} bytes)", state
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to read file '{path}': {e}"
                )
                return f"Failed to read file: {e}", state

        elif tool_name == "list_repo_directory":
            path = tool_args.get("path", "")
            branch = tool_args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                items = await github.get_directory_contents(path=path, ref=branch)
                
                # Format as a list
                lines = [f"📁 **Directory: {path or '/'}**", ""]
                for item in items:
                    icon = "📁" if item["type"] == "dir" else "📄"
                    size_info = f" ({item['size']} bytes)" if item["type"] == "file" and item.get("size") else ""
                    lines.append(f"  {icon} {item['name']}{size_info}")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                return f"Listed directory: {path or '/'} ({len(items)} items)", state
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to list directory '{path}': {e}"
                )
                return f"Failed to list directory: {e}", state

        elif tool_name == "get_repo_tree":
            branch = tool_args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                tree = await github.get_tree(ref=branch, recursive=True)
                
                # Format the tree - show files organized by directory
                lines = ["🌳 **Repository Structure**", ""]
                for item in tree[:300]:  # Limit to 300 items
                    icon = "📁" if item["type"] == "dir" else "📄"
                    lines.append(f"  {icon} {item['path']}")
                
                if len(tree) > 300:
                    lines.append(f"\n... and {len(tree) - 300} more items")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                return f"Repository tree: {len(tree)} items", state
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to get repository tree: {e}"
                )
                return f"Failed to get repository tree: {e}", state

        elif tool_name == "search_repo_code":
            query = tool_args.get("query", "")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                results = await github.search_code(query=query)
                
                lines = [f"🔍 **Search Results for: {query}**", ""]
                if results:
                    for item in results[:20]:
                        lines.append(f"📄 **{item['path']}**")
                        for match in item.get("text_matches", [])[:2]:
                            fragment = match.get("fragment", "")[:200]
                            lines.append(f"   ```{fragment}```")
                        lines.append("")
                else:
                    lines.append("No results found.")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                return f"Search complete: {len(results)} results for '{query}'", state
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to search code: {e}"
                )
                return f"Failed to search code: {e}", state
        
        return f"Unknown tool: {tool_name}", state
