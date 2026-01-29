# Agent Workflow Configuration Guide

This guide explains how to configure and customize the multi-agent workflows in the SDLC Agent system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Supervisor Agent                          │
│                   (Orchestrates entire SDLC)                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Requirements │       │  Development  │       │   Operations  │
│   Subgraph    │       │   Subgraph    │       │   Subgraph    │
└───────────────┘       └───────────────┘       └───────────────┘
        │                        │                        │
   ┌────┴────┐             ┌────┴────┐             ┌────┴────┐
   ▼         ▼             ▼         ▼             ▼         ▼
┌─────┐  ┌──────┐     ┌─────┐  ┌──────┐      ┌─────┐  ┌──────┐
│ BA  │  │ Arch │     │ Dev │  │ Test │      │ SRE │  │ Sec  │
└─────┘  └──────┘     └─────┘  └──────┘      └─────┘  └──────┘
```

---

## Agent Types

### 1. Orchestrator (Supervisor)
**Role**: High-level planning and task delegation
```python
# Configuration
ORCHESTRATOR_CONFIG = {
    "model": "gpt-4o",
    "system_prompt": "You are the lead software architect...",
    "capabilities": [
        "decompose_requirements",
        "assign_tasks",
        "coordinate_agents",
        "make_decisions",
    ],
}
```

### 2. Business Analyst Agent
**Role**: Requirements gathering and user story creation
```python
BA_AGENT_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "create_user_story",
        "analyze_requirements",
        "create_acceptance_criteria",
    ],
}
```

### 3. Architect Agent
**Role**: System design and technical specifications
```python
ARCHITECT_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "create_design_doc",
        "define_api_contract",
        "select_technologies",
    ],
}
```

### 4. Developer Agent
**Role**: Code implementation
```python
DEVELOPER_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "write_code",
        "refactor_code",
        "debug_code",
        "search_codebase",
    ],
}
```

### 5. Tester Agent
**Role**: Test creation and execution
```python
TESTER_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "generate_unit_tests",
        "generate_integration_tests",
        "run_tests",
        "analyze_coverage",
    ],
}
```

### 6. Code Reviewer Agent
**Role**: Code quality and standards
```python
REVIEWER_CONFIG = {
    "model": "claude-3-5-sonnet-20241022",
    "tools": [
        "review_code",
        "suggest_improvements",
        "check_standards",
    ],
}
```

### 7. Security Agent
**Role**: Security analysis and vulnerability detection
```python
SECURITY_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "scan_vulnerabilities",
        "check_dependencies",
        "review_secrets",
    ],
}
```

### 8. DevOps/SRE Agent
**Role**: Deployment and operations
```python
DEVOPS_CONFIG = {
    "model": "gpt-4o",
    "tools": [
        "create_dockerfile",
        "create_k8s_manifests",
        "setup_ci_cd",
        "monitor_deployment",
    ],
}
```

---

## Workflow States

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph

class SDLCState(TypedDict):
    # Project context
    project_id: str
    requirements: list[str]
    
    # Current phase
    phase: str  # requirements, design, development, testing, deployment
    
    # Artifacts
    user_stories: list[dict]
    design_docs: list[dict]
    code_files: list[dict]
    test_results: list[dict]
    
    # Messages
    messages: Annotated[list, add_messages]
    
    # Human-in-the-loop
    needs_human_input: bool
    human_feedback: str | None
```

---

## Creating a Workflow

### Basic Workflow Definition

```python
from langgraph.graph import StateGraph, END

def create_sdlc_workflow():
    # Create the graph
    workflow = StateGraph(SDLCState)
    
    # Add nodes (agents)
    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("requirements", requirements_subgraph)
    workflow.add_node("development", development_subgraph)
    workflow.add_node("testing", testing_subgraph)
    workflow.add_node("deployment", deployment_subgraph)
    workflow.add_node("human_review", human_review_node)
    
    # Define edges
    workflow.set_entry_point("orchestrator")
    
    workflow.add_conditional_edges(
        "orchestrator",
        route_to_phase,
        {
            "requirements": "requirements",
            "development": "development",
            "testing": "testing",
            "deployment": "deployment",
            "complete": END,
        }
    )
    
    # Human-in-the-loop
    workflow.add_conditional_edges(
        "development",
        check_human_review,
        {
            "needs_review": "human_review",
            "continue": "testing",
        }
    )
    
    return workflow.compile()
```

---

## Human-in-the-Loop (HITL)

Configure breakpoints for human approval:

```python
# Define HITL points
HITL_BREAKPOINTS = {
    "code_review": {
        "trigger": "after_code_generation",
        "message": "Code ready for review",
        "actions": ["approve", "request_changes", "reject"],
    },
    "deployment_approval": {
        "trigger": "before_production_deploy",
        "message": "Ready to deploy to production",
        "actions": ["approve", "reject"],
    },
    "security_review": {
        "trigger": "after_security_scan",
        "condition": lambda state: state["has_critical_vulnerabilities"],
        "message": "Critical vulnerabilities found",
        "actions": ["acknowledge", "fix_required"],
    },
}
```

### Implementing HITL

```python
async def human_review_node(state: SDLCState) -> SDLCState:
    """Pause for human input."""
    # This signals the workflow to pause
    return {
        **state,
        "needs_human_input": True,
        "pending_action": "code_review",
    }

def check_human_review(state: SDLCState) -> str:
    """Route based on human review result."""
    if state.get("needs_human_input"):
        return "needs_review"
    return "continue"
```

---

## Checkpointing

Enable workflow persistence for long-running tasks:

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Configure checkpointer
checkpointer = PostgresSaver.from_conn_string(
    settings.database.url,
    table_name="workflow_checkpoints",
)

# Compile with checkpointer
workflow = workflow.compile(checkpointer=checkpointer)

# Resume from checkpoint
config = {"configurable": {"thread_id": workflow_run_id}}
result = await workflow.ainvoke(state, config=config)
```

---

## Tool Configuration

### Adding Custom Tools

```python
from langchain.tools import tool
from pydantic import BaseModel, Field

class CodeSearchInput(BaseModel):
    query: str = Field(description="Search query")
    file_pattern: str = Field(default="**/*.py")

@tool(args_schema=CodeSearchInput)
async def search_codebase(query: str, file_pattern: str) -> str:
    """Search the codebase for relevant code."""
    # Implementation
    results = await vector_store.similarity_search(query)
    return format_results(results)

# Register tool with agent
developer_agent.tools.append(search_codebase)
```

### Tool Categories

```python
TOOL_CATEGORIES = {
    "code": [
        "write_code",
        "read_file", 
        "edit_file",
        "search_codebase",
        "run_command",
    ],
    "testing": [
        "run_tests",
        "generate_tests",
        "check_coverage",
    ],
    "analysis": [
        "analyze_code",
        "find_bugs",
        "security_scan",
    ],
    "documentation": [
        "generate_docs",
        "update_readme",
    ],
}
```

---

## Memory Configuration

### Vector Memory (Qdrant)

```python
from langchain_qdrant import Qdrant

# Configure vector store
vector_store = Qdrant(
    client=qdrant_client,
    collection_name="agent_memory",
    embeddings=embeddings,
)

# Store agent memories
await vector_store.aadd_documents([
    Document(
        page_content="Implementation details...",
        metadata={
            "agent": "developer",
            "project_id": project_id,
            "type": "code_context",
        }
    )
])

# Retrieve relevant context
context = await vector_store.asimilarity_search(
    query="authentication implementation",
    k=5,
    filter={"project_id": project_id},
)
```

---

## Workflow Monitoring

### Tracing with LangSmith

```python
import langsmith

# Enable tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
os.environ["LANGCHAIN_PROJECT"] = "sdlc-agent"
```

### Custom Callbacks

```python
from langchain.callbacks.base import BaseCallbackHandler

class WorkflowTracker(BaseCallbackHandler):
    async def on_chain_start(self, serialized, inputs, **kwargs):
        await self.log_event("workflow_step_started", inputs)
    
    async def on_chain_end(self, outputs, **kwargs):
        await self.log_event("workflow_step_completed", outputs)
    
    async def on_tool_start(self, serialized, input_str, **kwargs):
        await self.log_event("tool_invoked", {
            "tool": serialized["name"],
            "input": input_str,
        })
```

---

## Example: Feature Implementation Workflow

```python
async def run_feature_workflow(
    project_id: str,
    feature_request: str,
) -> dict:
    """Execute complete feature implementation workflow."""
    
    # Initialize state
    initial_state = SDLCState(
        project_id=project_id,
        requirements=[feature_request],
        phase="requirements",
        messages=[],
        needs_human_input=False,
    )
    
    # Run workflow
    config = {
        "configurable": {
            "thread_id": f"feature-{uuid4()}",
        },
        "callbacks": [WorkflowTracker()],
    }
    
    result = await sdlc_workflow.ainvoke(initial_state, config=config)
    
    return {
        "status": "completed",
        "artifacts": result["code_files"],
        "tests": result["test_results"],
    }
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_MAX_ITERATIONS` | Max reasoning iterations | 10 |
| `AGENT_TIMEOUT_SECONDS` | Timeout per agent call | 300 |
| `WORKFLOW_CHECKPOINT_ENABLED` | Enable persistence | true |
| `HITL_ENABLED` | Enable human review | true |
| `HITL_TIMEOUT_HOURS` | Human response timeout | 24 |

### Workflow Tuning

```python
WORKFLOW_CONFIG = {
    "max_retries": 3,
    "retry_delay": 5,
    "parallel_agents": 4,  # Max concurrent agent executions
    "memory_window": 20,   # Messages to keep in context
}
```
