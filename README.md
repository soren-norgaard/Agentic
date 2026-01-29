# Agentic SDLC

A multi-agent system for automating the entire software development lifecycle using LangGraph.

## Architecture

```
┌────────────────────────────────────────────┐
│          SDLC Orchestrator Agent           │
│  (Routes work, tracks state, coordinates)  │
└──────────────────┬─────────────────────────┘
                   │
  ┌────────────────┼────────────────┐
  ▼                ▼                ▼
┌──────────┐  ┌──────────┐    ┌──────────────┐
│ Require- │  │ Planning │    │ Development  │
│ ments    │─▶│  Agent   │───▶│    Crew      │
│ Agent    │  │          │    │ (Arch/Dev/CR)│
└──────────┘  └──────────┘    └──────┬───────┘
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
              ┌──────────┐   ┌────────────┐   ┌───────────┐
              │ QA Crew  │──▶│  Security  │──▶│  DevOps   │
              │(Unit/E2E)│   │   Agent    │   │   Crew    │
              └──────────┘   └────────────┘   └─────┬─────┘
                                                    ▼
                                            ┌─────────────┐
                                            │ Monitoring  │
                                            │ & Incident  │
                                            └─────────────┘
```

## Phases

| Phase | Agent(s) | Description |
|-------|----------|-------------|
| Requirements | RequirementsAgent | Parse objectives, generate user stories, clarify ambiguities |
| Planning | PlanningAgent | Break epics into stories, estimate complexity, prioritize |
| Development | ArchitectAgent, DeveloperAgent, CodeReviewAgent | Design, implement, and review code |
| Testing | UnitTestAgent, IntegrationTestAgent | Generate and run tests, measure coverage |
| Security | SecurityAgent | SAST/DAST scanning, vulnerability detection |
| Deployment | DevOpsAgent | CI/CD pipeline management, infrastructure |
| Operations | MonitoringAgent, IncidentAgent | Observability, alerting, incident response |

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the system
python -m agentic.main "Build a REST API for user management"
```

## Project Structure

```
agentic/
├── __init__.py
├── main.py                 # Entry point
├── config.py               # Configuration
├── state/                  # State schemas
│   ├── __init__.py
│   └── schemas.py
├── agents/                 # Agent implementations
│   ├── __init__.py
│   ├── base.py
│   ├── requirements.py
│   ├── planning.py
│   ├── architect.py
│   ├── developer.py
│   ├── code_review.py
│   ├── testing.py
│   ├── security.py
│   ├── devops.py
│   └── monitoring.py
├── orchestrator/           # Main orchestrator graph
│   ├── __init__.py
│   └── graph.py
├── tools/                  # Agent tools
│   ├── __init__.py
│   ├── file_tools.py
│   ├── git_tools.py
│   └── analysis_tools.py
└── memory/                 # Memory management
    ├── __init__.py
    └── store.py
```

## Configuration

Environment variables:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `LLM_PROVIDER` | LLM provider (openai/anthropic) |
| `LLM_MODEL` | Model name |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) |

## License

MIT
