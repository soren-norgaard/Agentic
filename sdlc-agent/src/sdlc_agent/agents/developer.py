# =============================================================================
# SDLC Agent - Developer Preparation Agent
# =============================================================================
# Agent responsible for preparing development work and handing off to GitHub.
# This agent creates comprehensive "Developer Briefs" rather than writing code.
#
# Philosophy: Agents prepare, humans implement (with Copilot assistance).
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
class DeveloperBrief:
    """
    A comprehensive brief for human developers.
    This is the primary output of the Developer Preparation Agent.
    """

    story_id: str
    story_title: str

    # Context
    requirements_addressed: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    architecture_context: str = ""

    # Analysis
    files_to_create: list[dict[str, str]] = field(default_factory=list)  # {path, purpose}
    files_to_modify: list[dict[str, str]] = field(default_factory=list)  # {path, changes}
    relevant_patterns: list[dict[str, str]] = field(
        default_factory=list
    )  # {pattern, location, description}

    # Implementation guidance
    suggested_approach: str = ""
    implementation_steps: list[str] = field(default_factory=list)
    potential_challenges: list[str] = field(default_factory=list)

    # Standards
    coding_standards: list[str] = field(default_factory=list)
    testing_requirements: list[str] = field(default_factory=list)

    # Handoff
    pre_implementation_checklist: list[str] = field(default_factory=list)
    definition_of_done: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert brief to Markdown for GitHub Issue comment."""
        lines = [
            f"## 🚀 Developer Brief: {self.story_title}",
            "",
            "This brief has been prepared by the Developer Preparation Agent to help you implement this story.",
            "",
        ]

        # Requirements Traceability
        if self.requirements_addressed:
            lines.extend(
                [
                    "### 📋 Requirements Traceability",
                    "",
                    "This story addresses the following requirements:",
                    "",
                ]
            )
            for req in self.requirements_addressed:
                lines.append(f"- `{req}`")
            lines.append("")

        # Acceptance Criteria
        if self.acceptance_criteria:
            lines.extend(
                [
                    "### ✅ Acceptance Criteria",
                    "",
                ]
            )
            for i, ac in enumerate(self.acceptance_criteria, 1):
                lines.append(f"{i}. {ac}")
            lines.append("")

        # Architecture Context
        if self.architecture_context:
            lines.extend(
                [
                    "### 🏗️ Architecture Context",
                    "",
                    self.architecture_context,
                    "",
                ]
            )

        # Files to Create
        if self.files_to_create:
            lines.extend(
                [
                    "### 📁 Files to Create",
                    "",
                    "| File Path | Purpose |",
                    "|-----------|---------|",
                ]
            )
            for f in self.files_to_create:
                lines.append(f"| `{f.get('path', '')}` | {f.get('purpose', '')} |")
            lines.append("")

        # Files to Modify
        if self.files_to_modify:
            lines.extend(
                [
                    "### ✏️ Files to Modify",
                    "",
                    "| File Path | Changes Needed |",
                    "|-----------|----------------|",
                ]
            )
            for f in self.files_to_modify:
                lines.append(f"| `{f.get('path', '')}` | {f.get('changes', '')} |")
            lines.append("")

        # Relevant Patterns
        if self.relevant_patterns:
            lines.extend(
                [
                    "### 🔍 Relevant Code Patterns",
                    "",
                    "Reference these existing patterns in the codebase:",
                    "",
                ]
            )
            for p in self.relevant_patterns:
                lines.append(f"**{p.get('pattern', '')}** in `{p.get('location', '')}`")
                lines.append(f"> {p.get('description', '')}")
                lines.append("")

        # Suggested Approach
        if self.suggested_approach:
            lines.extend(
                [
                    "### 💡 Suggested Approach",
                    "",
                    self.suggested_approach,
                    "",
                ]
            )

        # Implementation Steps
        if self.implementation_steps:
            lines.extend(
                [
                    "### 📝 Implementation Steps",
                    "",
                ]
            )
            for i, step in enumerate(self.implementation_steps, 1):
                lines.append(f"{i}. [ ] {step}")
            lines.append("")

        # Potential Challenges
        if self.potential_challenges:
            lines.extend(
                [
                    "### ⚠️ Potential Challenges",
                    "",
                ]
            )
            for challenge in self.potential_challenges:
                lines.append(f"- {challenge}")
            lines.append("")

        # Coding Standards
        if self.coding_standards:
            lines.extend(
                [
                    "### 📏 Coding Standards (from instruction file)",
                    "",
                ]
            )
            for standard in self.coding_standards:
                lines.append(f"- {standard}")
            lines.append("")

        # Testing Requirements
        if self.testing_requirements:
            lines.extend(
                [
                    "### 🧪 Testing Requirements",
                    "",
                ]
            )
            for req in self.testing_requirements:
                lines.append(f"- {req}")
            lines.append("")

        # Pre-implementation Checklist
        lines.extend(
            [
                "### 🔧 Pre-Implementation Checklist",
                "",
            ]
        )
        checklist = self.pre_implementation_checklist or [
            "Read and understand the acceptance criteria",
            "Review the architecture context",
            "Create a feature branch from main",
            "Set up local development environment",
        ]
        for item in checklist:
            lines.append(f"- [ ] {item}")
        lines.append("")

        # Definition of Done
        lines.extend(
            [
                "### 🏁 Definition of Done",
                "",
            ]
        )
        dod = self.definition_of_done or [
            "All acceptance criteria are met",
            "Code follows project coding standards",
            "Unit tests written and passing",
            "No new linting errors",
            "PR opened and linked to this issue",
            "PR description explains implementation decisions",
        ]
        for item in dod:
            lines.append(f"- [ ] {item}")
        lines.append("")

        # Footer
        story_slug = self.story_title.lower().replace(" ", "-")[:30]
        lines.extend(
            [
                "---",
                "",
                "💬 **Ready to start?** Open VS Code, create your branch, and use Copilot Chat for assistance!",
                "",
                "```",
                f"git checkout -b feature/{self.story_id}-{story_slug}",
                "```",
            ]
        )

        return "\n".join(lines)


@dataclass
class DeveloperState(AgentState):
    """State specific to the developer preparation agent."""

    # Current story context
    current_story: dict[str, Any] | None = None
    architecture_context: dict[str, Any] | None = None

    # Analysis results
    codebase_analysis: dict[str, Any] = field(default_factory=dict)
    identified_files: list[dict[str, Any]] = field(default_factory=list)
    code_patterns: list[dict[str, Any]] = field(default_factory=list)

    # Developer brief
    developer_brief: DeveloperBrief | None = None

    # Handoff tracking
    handoff_complete: bool = False
    github_issue_number: int | None = None


class DeveloperAgent(BaseAgent[DeveloperState]):
    """
    Developer Preparation Agent.

    This agent does NOT write production code. Instead, it:
    1. Analyzes the codebase to understand patterns and structure
    2. Creates a comprehensive "Developer Brief" with all context
    3. Hands off to GitHub for human implementation (with Copilot assistance)

    Philosophy: Agents prepare, humans implement.

    Responsibilities:
    - Understand story requirements and acceptance criteria
    - Analyze codebase for relevant patterns and files
    - Create implementation guidance
    - Generate a Developer Brief for the GitHub Issue
    - Hand off to human developers with full context
    """

    name = "developer"
    description = "Prepares development work and creates Developer Briefs for handoff"
    phase = AgentPhase.DEVELOPMENT

    @property
    def system_prompt(self) -> str:
        return """You are the Developer Preparation Agent. Your job is to prepare comprehensive 
"Developer Briefs" that help human developers implement stories efficiently.

**IMPORTANT: You do NOT write production code.** You prepare and hand off.

## WORKFLOW - FOLLOW THESE STEPS IN ORDER:

### Step 1: Check for Stories
1. Use `list_available_stories` to see all stories that need Developer Briefs
2. If stories exist: Use `select_story` to pick one to work on
3. If NO stories exist: Create a brief based on the task context you received from the orchestrator

### Step 2: Analyze the Codebase (if GitHub repo is configured)
- Use `get_repo_tree` to see the repository structure
- Use `read_repo_file` to read relevant files
- Use `search_repo_code` to find patterns and examples
- Identify files to create/modify

### Step 3: Create the Developer Brief
- Use the tools to build up the brief: analyze_story, identify_files, find_code_patterns, etc.
- Use `generate_developer_brief` to create the final brief
- **IMPORTANT**: Always call `generate_developer_brief` at the end to save your work!

### Step 4: Hand Off
- Use `post_brief_to_github` to add the brief as a comment on the GitHub Issue (if available)
- Use `complete_handoff` when done with ALL stories

**If No Stories Are Available:**
Create a developer brief based on the task context from the orchestrator. Extract:
- What needs to be built (from the task description)
- Acceptance criteria
- Technical approach
Then use `generate_developer_brief` to save the brief.

**GitHub Repository Access:**
You have tools to read the actual GitHub repository:
- `read_repo_file` - Read a specific file's contents
- `list_repo_directory` - List files in a directory
- `get_repo_tree` - Get the full repository structure
- `search_repo_code` - Search for code patterns/keywords

USE THESE TOOLS to understand the actual codebase before creating your brief.

What makes a good Developer Brief:
- Clear traceability to requirements
- Specific files to create/modify with purposes
- References to existing patterns to follow (from actual code you read)
- Step-by-step implementation guidance
- Potential challenges called out
- Testing requirements
- Definition of Done checklist

Remember: A human developer with Copilot assistance will do the actual implementation.
Your job is to give them everything they need to succeed quickly."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            # Story selection tools (use these first!)
            ToolDefinition(
                name="list_available_stories",
                description="List all available user stories that need developer briefs. Use this FIRST to see what stories are available to work on.",
                parameters=[],
            ),
            ToolDefinition(
                name="select_story",
                description="Select a story to prepare a Developer Brief for. Call this after listing stories to pick one to work on.",
                parameters=[
                    ToolParameter(
                        name="story_id",
                        description="The ID of the story to select (from list_available_stories)",
                    ),
                ],
            ),
            ToolDefinition(
                name="analyze_story",
                description="Analyze the current story to extract key implementation details",
                parameters=[
                    ToolParameter(
                        name="story_summary",
                        description="Your summary of what needs to be implemented",
                    ),
                    ToolParameter(
                        name="key_requirements",
                        description="JSON array of key requirements extracted from the story",
                    ),
                ],
            ),
            ToolDefinition(
                name="identify_files",
                description="Identify files that need to be created or modified",
                parameters=[
                    ToolParameter(
                        name="files_to_create",
                        description="JSON array of {path, purpose} for new files",
                    ),
                    ToolParameter(
                        name="files_to_modify",
                        description="JSON array of {path, changes} for existing files",
                    ),
                ],
            ),
            ToolDefinition(
                name="find_code_patterns",
                description="Identify relevant code patterns in the codebase to follow",
                parameters=[
                    ToolParameter(
                        name="patterns",
                        description="JSON array of {pattern, location, description}",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_implementation_plan",
                description="Create a step-by-step implementation plan",
                parameters=[
                    ToolParameter(
                        name="approach",
                        description="High-level description of the implementation approach",
                    ),
                    ToolParameter(
                        name="steps",
                        description="JSON array of implementation steps",
                    ),
                    ToolParameter(
                        name="challenges",
                        description="JSON array of potential challenges",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="extract_coding_standards",
                description="Extract relevant coding standards from the project",
                parameters=[
                    ToolParameter(
                        name="standards",
                        description="JSON array of relevant coding standards",
                    ),
                    ToolParameter(
                        name="testing_requirements",
                        description="JSON array of testing requirements",
                    ),
                ],
            ),
            ToolDefinition(
                name="generate_developer_brief",
                description="Generate the final Developer Brief with all gathered information. If no story is selected, provide story_id and story_title from the task context.",
                parameters=[
                    ToolParameter(
                        name="story_id",
                        description="Story ID (optional if a story is selected, required otherwise)",
                        required=False,
                    ),
                    ToolParameter(
                        name="story_title",
                        description="Story title (optional if a story is selected, required otherwise)",
                        required=False,
                    ),
                    ToolParameter(
                        name="requirements_addressed",
                        description="JSON array of requirement IDs this story addresses",
                    ),
                    ToolParameter(
                        name="architecture_context",
                        description="Summary of relevant architecture context",
                    ),
                    ToolParameter(
                        name="acceptance_criteria",
                        description="JSON array of acceptance criteria (optional if a story is selected)",
                        required=False,
                    ),
                    ToolParameter(
                        name="implementation_steps",
                        description="JSON array of implementation steps",
                        required=False,
                    ),
                    ToolParameter(
                        name="pre_implementation_checklist",
                        description="JSON array of items to check before starting",
                        required=False,
                    ),
                    ToolParameter(
                        name="definition_of_done",
                        description="JSON array of Definition of Done items",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="post_brief_to_github",
                description="Post the Developer Brief as a comment on the GitHub Issue",
                parameters=[
                    ToolParameter(
                        name="issue_number",
                        description="GitHub Issue number to post the comment on",
                        type="integer",
                    ),
                    ToolParameter(
                        name="add_label",
                        description="Label to add to the issue (default: ready-for-dev)",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_handoff",
                description="Mark the handoff as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of what was prepared",
                    ),
                    ToolParameter(
                        name="github_issue_url",
                        description="URL to the GitHub Issue with the brief",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="request_clarification",
                description="Request clarification on requirements before preparing brief",
                parameters=[
                    ToolParameter(
                        name="question",
                        description="The clarification question",
                    ),
                    ToolParameter(
                        name="context",
                        description="Context for why this clarification is needed",
                    ),
                ],
            ),
            # GitHub repository reading tools
            ToolDefinition(
                name="read_repo_file",
                description="Read the contents of a file from the GitHub repository",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to the file in the repository (e.g., 'src/main.py')",
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
                description="Search for code patterns or keywords in the repository",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (e.g., 'function authenticate' or 'class UserService')",
                    ),
                ],
            ),
        ]

    async def process(self, state: DeveloperState) -> DeveloperState:
        """Process the current state and prepare the developer brief."""
        state.iteration_count += 1
        self.logger.info(
            "Developer Preparation Agent processing",
            iteration=state.iteration_count,
            story=state.current_story.get("id") if state.current_story else None,
        )

        # EFFICIENCY OPTIMIZATION: Auto-generate briefs for all stories in a single iteration
        # This prevents running out of iterations before generating any briefs
        await self._auto_generate_briefs(state)
        
        # Check if we've already generated briefs for all stories
        if getattr(state, '_briefs_generated', False):
            self.logger.info("All briefs already generated, completing handoff")
            state.handoff_complete = True
            state.add_message(
                MessageRole.ASSISTANT,
                "Developer briefs have been generated for all available stories. Development phase complete."
            )
            return state

        # Build messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for msg in state.messages[-10:]:
            messages.append(msg.to_dict())

        # Build context prompt
        context_parts = ["## Current Task: Prepare Developer Brief", ""]

        # If no story selected, show available stories
        if not state.current_story:
            # Get stories from state (SDLCState has user_stories field)
            stories = getattr(state, 'user_stories', []) or getattr(state, 'stories', []) or []
            if stories:
                context_parts.append("### ⚠️ NO STORY SELECTED")
                context_parts.append("")
                context_parts.append("You must first select a story to work on!")
                context_parts.append("Use `list_available_stories` to see available stories,")
                context_parts.append("then use `select_story` to pick one.")
                context_parts.append("")
                context_parts.append(f"There are {len(stories)} stories available.")
                context_parts.append("")
            else:
                context_parts.append("### No Stories Available")
                context_parts.append("No user stories have been created yet.")
                context_parts.append("Use `complete_handoff` to mark development phase complete.")
                context_parts.append("")

        if state.current_story:
            context_parts.append("### Story Details")
            context_parts.append(f"**ID:** {state.current_story.get('id')}")
            context_parts.append(f"**Title:** {state.current_story.get('title')}")
            context_parts.append(
                f"**Description:** {state.current_story.get('description')}"
            )

            ac = state.current_story.get("acceptance_criteria", [])
            if ac:
                context_parts.append("\n**Acceptance Criteria:**")
                for criterion in ac:
                    if isinstance(criterion, dict):
                        context_parts.append(f"- {criterion.get('criteria', criterion)}")
                    else:
                        context_parts.append(f"- {criterion}")

            req_ids = state.current_story.get("requirement_ids", [])
            if req_ids:
                context_parts.append(f"\n**Linked Requirements:** {', '.join(req_ids)}")

            context_parts.append("")

        if state.architecture_context:
            context_parts.append("### Architecture Context")
            context_parts.append(str(state.architecture_context))
            context_parts.append("")

        if state.codebase_analysis:
            context_parts.append("### Codebase Analysis (so far)")
            context_parts.append(str(state.codebase_analysis))
            context_parts.append("")

        if state.identified_files:
            context_parts.append("### Files Identified")
            for f in state.identified_files:
                context_parts.append(
                    f"- {f.get('path')}: {f.get('purpose') or f.get('changes')}"
                )
            context_parts.append("")

        if state.code_patterns:
            context_parts.append("### Code Patterns Found")
            for p in state.code_patterns:
                context_parts.append(f"- {p.get('pattern')} in {p.get('location')}")
            context_parts.append("")

        if state.developer_brief:
            context_parts.append("### Developer Brief Status")
            context_parts.append("Brief has been generated. Ready to post to GitHub.")
            context_parts.append("")

        context_parts.append("---")
        context_parts.append(
            "What should we do next to prepare this story for development?"
        )

        messages.append({"role": "user", "content": "\n".join(context_parts)})

        # Call LLM
        tools = [t.to_openai_schema() for t in self.tools]
        response = await self._call_llm(messages, tools)

        # Process response
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        state.add_message(MessageRole.ASSISTANT, content)

        if tool_calls:
            for tool_call in tool_calls:
                await self._handle_tool_call(state, tool_call)

        return state

    async def _auto_generate_briefs(self, state: DeveloperState) -> None:
        """
        Automatically generate developer briefs for all stories.
        This is called at the start of processing to ensure briefs are created
        even if the workflow is running low on iterations.
        """
        import uuid as uuid_module
        
        # Check if we've already generated briefs
        if getattr(state, '_briefs_generated', False):
            return
            
        # Get stories from state or database
        stories = getattr(state, 'user_stories', []) or getattr(state, 'stories', []) or []
        
        # If no stories in state, try loading from database
        if not stories and state.project_id:
            try:
                from sdlc_agent.db import get_session, Task, TaskType
                from sqlalchemy import select
                import uuid
                
                async with get_session() as session:
                    project_uuid = uuid.UUID(state.project_id) if isinstance(state.project_id, str) else state.project_id
                    query = select(Task).where(
                        Task.project_id == project_uuid,
                        Task.task_type == TaskType.STORY,
                    )
                    result = await session.execute(query)
                    db_stories = result.scalars().all()
                    
                    if db_stories:
                        stories = [
                            {
                                "id": str(s.id),
                                "title": s.title,
                                "description": s.description or "",
                                "status": s.status.value if s.status else "open",
                                "story_points": s.story_points,
                                "acceptance_criteria": s.extra_data.get("acceptance_criteria", []) if s.extra_data else [],
                            }
                            for s in db_stories
                        ]
                        self.logger.info("Loaded stories from database for auto-brief", count=len(stories))
            except Exception as e:
                self.logger.warning("Failed to load stories from database", error=str(e))
        
        if not stories:
            self.logger.info("No stories available for auto-brief generation")
            state._briefs_generated = True
            return
            
        self.logger.info("Auto-generating developer briefs", story_count=len(stories))
        
        # Generate a brief for each story
        from sdlc_agent.db import Artifact, get_session_context
        
        briefs_created = 0
        for story in stories:
            try:
                story_id = story.get('id', 'unknown')
                story_title = story.get('title', 'Untitled Story')
                description = story.get('description', '')
                acceptance_criteria = story.get('acceptance_criteria', [])
                
                # Normalize acceptance criteria
                if isinstance(acceptance_criteria, str):
                    import json
                    try:
                        acceptance_criteria = json.loads(acceptance_criteria)
                    except:
                        acceptance_criteria = [acceptance_criteria]
                
                # Create a basic developer brief
                brief = DeveloperBrief(
                    story_id=story_id,
                    story_title=story_title,
                    acceptance_criteria=acceptance_criteria if isinstance(acceptance_criteria, list) else [],
                    suggested_approach=f"Implement the functionality described in: {description[:500]}..." if len(description) > 500 else f"Implement: {description}",
                    implementation_steps=[
                        "Review the acceptance criteria and understand the requirements",
                        "Identify relevant files and components in the codebase",
                        "Create or modify files as needed to implement the feature",
                        "Write unit tests to cover the new functionality",
                        "Update documentation if applicable",
                        "Create a pull request with a clear description linking to this story",
                    ],
                    pre_implementation_checklist=[
                        "Understand the story requirements and acceptance criteria",
                        "Review related code and patterns in the codebase",
                        "Set up local development environment",
                        "Create a feature branch from main/develop",
                    ],
                    definition_of_done=[
                        "All acceptance criteria are met",
                        "Code is reviewed and approved",
                        "Unit tests pass with adequate coverage",
                        "Documentation is updated",
                        "Feature is deployed to staging/test environment",
                    ],
                )
                
                # Save to database
                async with get_session_context() as session:
                    artifact = Artifact(
                        workflow_id=uuid_module.UUID(state.workflow_id),
                        name=f"Developer Brief - {story_title}",
                        artifact_type="developer_brief",
                        content=brief.to_markdown(),
                        extra_data={
                            "story_id": story_id,
                            "story_title": story_title,
                            "auto_generated": True,
                        },
                    )
                    session.add(artifact)
                    await session.commit()
                    
                briefs_created += 1
                self.logger.info(
                    "Auto-generated developer brief",
                    story_id=story_id,
                    story_title=story_title,
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to auto-generate brief for story",
                    story_id=story.get('id'),
                    error=str(e),
                )
        
        state._briefs_generated = True
        self.logger.info("Auto-brief generation complete", briefs_created=briefs_created)
        
        if briefs_created > 0:
            state.add_message(
                MessageRole.ASSISTANT,
                f"✅ Generated {briefs_created} developer briefs automatically for the available stories.",
            )

    async def _save_developer_brief_to_db(self, state: DeveloperState) -> None:
        """Save the developer brief as an artifact in the database.
        
        This method implements deduplication: if a developer brief already exists
        for the same story_id and workflow_id, it updates the existing one instead
        of creating a duplicate.
        """
        import uuid as uuid_module
        
        try:
            from sdlc_agent.db import Artifact, get_session_context
            from sqlalchemy import select
            
            if not state.developer_brief:
                return
                
            story = state.current_story or {}
            story_id = story.get('id') or state.developer_brief.story_id
            story_title = story.get('title', state.developer_brief.story_title or 'Story')
            workflow_uuid = uuid_module.UUID(state.workflow_id)
            
            async with get_session_context() as session:
                # Check if a developer brief already exists for this story and workflow
                existing_query = select(Artifact).where(
                    Artifact.workflow_id == workflow_uuid,
                    Artifact.artifact_type == "developer_brief",
                    Artifact.extra_data["story_id"].astext == str(story_id),
                )
                result = await session.execute(existing_query)
                existing_artifact = result.scalar_one_or_none()
                
                if existing_artifact:
                    # Update existing artifact instead of creating a duplicate
                    existing_artifact.content = state.developer_brief.to_markdown()
                    existing_artifact.extra_data = {
                        "story_id": story_id,
                        "story_title": story_title,
                        "github_issue_number": state.github_issue_number,
                    }
                    self.logger.info(
                        "Updated existing developer brief in database",
                        workflow_id=state.workflow_id,
                        story_id=story_id,
                        story_title=story_title,
                    )
                else:
                    # Create new artifact
                    artifact = Artifact(
                        workflow_id=workflow_uuid,
                        name=f"Developer Brief - {story_title}",
                        artifact_type="developer_brief",
                        content=state.developer_brief.to_markdown(),
                        extra_data={
                            "story_id": story_id,
                            "story_title": story_title,
                            "github_issue_number": state.github_issue_number,
                        },
                    )
                    session.add(artifact)
                    self.logger.info(
                        "Developer brief saved to database",
                        workflow_id=state.workflow_id,
                        story_id=story_id,
                        story_title=story_title,
                    )
                    
                await session.commit()
        except Exception as e:
            self.logger.warning(
                "Failed to save developer brief to database",
                error=str(e),
            )

    async def _handle_tool_call(
        self, state: DeveloperState, tool_call: dict[str, Any]
    ) -> None:
        """Handle a tool call from the LLM."""
        import json

        # Handle both OpenAI format (function.name) and parsed format (name)
        if "function" in tool_call:
            name = tool_call["function"].get("name", "")
            args_str = tool_call["function"].get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
        else:
            name = tool_call.get("name", "")
            args = tool_call.get("args", {})

        self.logger.info("Handling tool call", tool=name, args=args)

        if name == "list_available_stories":
            # List all available stories from state
            user_stories = getattr(state, 'user_stories', []) or []
            stories_field = getattr(state, 'stories', []) or []
            stories = user_stories or stories_field
            
            # If no stories in state, try loading from database
            if not stories and state.project_id:
                try:
                    from sdlc_agent.db import get_session, Task, TaskType
                    from sqlalchemy import select
                    import uuid
                    
                    async with get_session() as session:
                        # Get stories from database
                        project_uuid = uuid.UUID(state.project_id) if isinstance(state.project_id, str) else state.project_id
                        query = select(Task).where(
                            Task.project_id == project_uuid,
                            Task.task_type == TaskType.STORY,
                        )
                        result = await session.execute(query)
                        db_stories = result.scalars().all()
                        
                        if db_stories:
                            stories = [
                                {
                                    "id": str(s.id),
                                    "title": s.title,
                                    "description": s.description,
                                    "status": s.status.value if s.status else "open",
                                    "story_points": s.story_points,
                                }
                                for s in db_stories
                            ]
                            # Also save to state for future use
                            if hasattr(state, 'user_stories'):
                                state.user_stories = stories
                            self.logger.info("Loaded stories from database", count=len(stories))
                except Exception as e:
                    self.logger.warning("Failed to load stories from database", error=str(e))
            
            self.logger.info(
                "Listing available stories",
                user_stories_count=len(user_stories),
                stories_field_count=len(stories_field),
                total=len(stories),
            )
            
            if stories:
                story_list = []
                for i, story in enumerate(stories, 1):
                    story_id = story.get('id', f'story-{i}')
                    title = story.get('title', 'Untitled')
                    status = story.get('status', 'open')
                    story_list.append(f"{i}. [{story_id}] {title} (status: {status})")
                state.add_message(
                    MessageRole.TOOL,
                    f"Available stories ({len(stories)}):\n" + "\n".join(story_list) +
                    "\n\nUse `select_story` with the story ID to select one.",
                    tool_call_id=tool_call.get("id", ""),
                )
            else:
                # No stories - the agent should create a brief based on the task context
                state.add_message(
                    MessageRole.TOOL,
                    "No user stories found. You should create a developer brief based on the task context provided by the orchestrator. Use `generate_developer_brief` with the information from your task context.",
                    tool_call_id=tool_call.get("id", ""),
                )

        elif name == "select_story":
            story_id = args.get("story_id", "")
            # Also try loading from database for select
            user_stories = getattr(state, 'user_stories', []) or []
            stories_field = getattr(state, 'stories', []) or []
            stories = user_stories or stories_field
            
            # Find the story by ID
            selected = None
            for story in stories:
                if story.get('id') == story_id or str(story.get('id')) == story_id:
                    selected = story
                    break
            
            if selected:
                state.current_story = selected
                state.add_message(
                    MessageRole.TOOL,
                    f"Selected story: {selected.get('title', 'Untitled')}\n\n" +
                    f"Description: {selected.get('description', 'No description')}\n\n" +
                    "Now analyze the codebase and prepare the Developer Brief.",
                    tool_call_id=tool_call.get("id", ""),
                )
                self.logger.info("Story selected", story_id=story_id, title=selected.get('title'))
            else:
                state.add_message(
                    MessageRole.TOOL,
                    f"Story not found with ID: {story_id}. Use `list_available_stories` to see valid IDs.",
                    tool_call_id=tool_call.get("id", ""),
                )

        elif name == "analyze_story":
            state.codebase_analysis["story_summary"] = args.get("story_summary")
            try:
                state.codebase_analysis["key_requirements"] = json.loads(
                    args.get("key_requirements", "[]")
                )
            except json.JSONDecodeError:
                state.codebase_analysis["key_requirements"] = []

        elif name == "identify_files":
            try:
                files_to_create = json.loads(args.get("files_to_create", "[]"))
                files_to_modify = json.loads(args.get("files_to_modify", "[]"))
                state.identified_files = [
                    {"type": "create", **f} for f in files_to_create
                ] + [{"type": "modify", **f} for f in files_to_modify]
            except json.JSONDecodeError:
                pass

        elif name == "find_code_patterns":
            try:
                state.code_patterns = json.loads(args.get("patterns", "[]"))
            except json.JSONDecodeError:
                pass

        elif name == "create_implementation_plan":
            state.codebase_analysis["approach"] = args.get("approach")
            try:
                state.codebase_analysis["steps"] = json.loads(args.get("steps", "[]"))
                state.codebase_analysis["challenges"] = json.loads(
                    args.get("challenges", "[]")
                )
            except json.JSONDecodeError:
                pass

        elif name == "extract_coding_standards":
            try:
                state.codebase_analysis["coding_standards"] = json.loads(
                    args.get("standards", "[]")
                )
                state.codebase_analysis["testing_requirements"] = json.loads(
                    args.get("testing_requirements", "[]")
                )
            except json.JSONDecodeError:
                pass

        elif name == "generate_developer_brief":
            # Create the developer brief from all gathered information
            story = state.current_story or {}
            analysis = state.codebase_analysis

            # Get story ID and title from args or story
            story_id = args.get("story_id") or story.get("id", "BRIEF-001")
            story_title = args.get("story_title") or story.get("title", "Developer Brief")

            try:
                req_ids = json.loads(args.get("requirements_addressed", "[]"))
            except json.JSONDecodeError:
                req_ids = story.get("requirement_ids", [])

            try:
                pre_checklist = json.loads(
                    args.get("pre_implementation_checklist", "[]")
                )
            except json.JSONDecodeError:
                pre_checklist = []

            try:
                dod = json.loads(args.get("definition_of_done", "[]"))
            except json.JSONDecodeError:
                dod = []
            
            try:
                impl_steps = json.loads(args.get("implementation_steps", "[]"))
            except json.JSONDecodeError:
                impl_steps = analysis.get("steps", [])

            # Extract acceptance criteria from args or story
            ac_list = []
            if args.get("acceptance_criteria"):
                try:
                    ac_list = json.loads(args.get("acceptance_criteria", "[]"))
                except json.JSONDecodeError:
                    pass
            
            if not ac_list:
                ac = story.get("acceptance_criteria", [])
                for criterion in ac:
                    if isinstance(criterion, dict):
                        ac_list.append(criterion.get("criteria", str(criterion)))
                    else:
                        ac_list.append(str(criterion))

            state.developer_brief = DeveloperBrief(
                story_id=story_id,
                story_title=story_title,
                requirements_addressed=req_ids,
                acceptance_criteria=ac_list,
                architecture_context=args.get("architecture_context", ""),
                files_to_create=[
                    f for f in state.identified_files if f.get("type") == "create"
                ],
                files_to_modify=[
                    f for f in state.identified_files if f.get("type") == "modify"
                ],
                relevant_patterns=state.code_patterns,
                suggested_approach=analysis.get("approach", ""),
                implementation_steps=impl_steps,
                potential_challenges=analysis.get("challenges", []),
                coding_standards=analysis.get("coding_standards", []),
                testing_requirements=analysis.get("testing_requirements", []),
                pre_implementation_checklist=pre_checklist,
                definition_of_done=dod,
            )

            # Add the brief as an artifact to state
            state.add_artifact(
                name=f"Developer Brief - {story_title}",
                artifact_type="developer_brief",
                content=state.developer_brief.to_markdown(),
            )
            
            # Also save to database immediately
            await self._save_developer_brief_to_db(state)
            
            # Confirm to LLM that brief was created
            state.add_message(
                MessageRole.TOOL,
                f"✅ Developer Brief created and saved for: {story_title}\n\nYou can now use `complete_handoff` to finish.",
                tool_call_id=tool_call.get("id", ""),
            )

        elif name == "post_brief_to_github":
            issue_number = args.get("issue_number")
            label = args.get("add_label", "ready-for-dev")

            if state.developer_brief and issue_number:
                try:
                    from sdlc_agent.services.github_service import GitHubService

                    github = GitHubService()

                    # Post the brief as a comment
                    await github.add_issue_comment(
                        issue_number=issue_number,
                        body=state.developer_brief.to_markdown(),
                    )

                    # Add the label
                    await github.add_labels(
                        issue_number=issue_number,
                        labels=[label],
                    )

                    state.github_issue_number = issue_number
                    self.logger.info(
                        "Posted Developer Brief to GitHub",
                        issue_number=issue_number,
                        label=label,
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to post to GitHub",
                        error=str(e),
                    )
                    # Still mark the brief as created even if GitHub fails
                    state.add_message(
                        MessageRole.SYSTEM,
                        f"Note: Failed to post to GitHub ({e}). Brief is available in artifacts.",
                    )

        elif name == "complete_handoff":
            state.handoff_complete = True
            summary = args.get("summary", "Developer Brief prepared")

            state.add_message(
                MessageRole.ASSISTANT,
                f"✅ **Handoff Complete**\n\n{summary}\n\n"
                f"The story is now ready for human development with Copilot assistance.",
            )

            # Mark development phase as completed
            if hasattr(state, 'phases_completed') and 'development' not in state.phases_completed:
                state.phases_completed.append('development')

            # Move to next phase (code review will wait for PR)
            state.phase = AgentPhase.CODE_REVIEW

        elif name == "request_clarification":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "clarification",
                "question": args.get("question"),
                "context": args.get("context"),
            }

        elif name == "read_repo_file":
            path = args.get("path", "")
            branch = args.get("branch")
            
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
                self.logger.info("Read repository file", path=path, size=file_data.get("size"))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to read file '{path}': {e}"
                )

        elif name == "list_repo_directory":
            path = args.get("path", "")
            branch = args.get("branch")
            
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
                self.logger.info("Listed directory", path=path, items=len(items))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to list directory '{path}': {e}"
                )

        elif name == "get_repo_tree":
            branch = args.get("branch")
            
            try:
                from sdlc_agent.services.github_service import GitHubService
                github = GitHubService()
                
                tree = await github.get_tree(ref=branch, recursive=True)
                
                # Format the tree
                lines = ["🌳 **Repository Structure**", ""]
                for item in tree[:200]:  # Limit to 200 items
                    indent = "  " * item["path"].count("/")
                    icon = "📁" if item["type"] == "dir" else "📄"
                    lines.append(f"{indent}{icon} {item['path'].split('/')[-1]}")
                
                if len(tree) > 200:
                    lines.append(f"\n... and {len(tree) - 200} more items")
                
                state.add_message(MessageRole.SYSTEM, "\n".join(lines))
                self.logger.info("Got repository tree", total_items=len(tree))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to get repository tree: {e}"
                )

        elif name == "search_repo_code":
            query = args.get("query", "")
            
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
                self.logger.info("Searched code", query=query, results=len(results))
            except Exception as e:
                state.add_message(
                    MessageRole.SYSTEM,
                    f"❌ Failed to search code: {e}"
                )
