# SDLC Agent - Multi-Agent Software Development Lifecycle System

Enterprise-grade multi-agent system for automated software development lifecycle management. From requirements to deployment, powered by LangGraph and modern AI orchestration.

## 🎯 Overview

SDLC Agent automates the complete software development lifecycle using specialized AI agents:

```
Requirements → Planning → Design → Development → Testing → Security → Deployment → Operations
```

### Key Features

- **🤖 Multi-Agent Orchestration** - Hierarchical agent system with specialized roles
- **🔄 Full SDLC Coverage** - Requirements analysis to production monitoring
- **👤 Human-in-the-Loop** - Configurable approval gates and escalation
- **📊 Real-time Visibility** - Live agent activity and workflow progress
- **🔐 Enterprise Security** - Audit logging, RBAC, secrets management
- **📈 Observability** - OpenTelemetry tracing, metrics, and logging
- **🐳 Docker Ready** - Complete containerized infrastructure

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│   Dashboard │ Workflows │ Projects │ Activity │ Human Input     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       API Gateway (FastAPI)                      │
│     REST API │ WebSocket │ Auth │ Rate Limiting │ CORS          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Agent Orchestration (LangGraph)               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Orchestrator Agent                      │  │
│  │         (Delegation, Routing, Progress Tracking)           │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌──────────┐ ┌──────────┐ ┌▼─────────┐ ┌──────────┐ ┌────────┐ │
│  │Requirements│ │ Planning │ │Developer │ │ Testing  │ │Security│ │
│  │   Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │ Agent  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐                                      │
│  │Code Review│ │  DevOps  │                                      │
│  │   Agent   │ │  Agent   │                                      │
│  └──────────┘ └──────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                        Infrastructure                            │
│   PostgreSQL │ Redis │ Qdrant │ MinIO │ OpenTelemetry Stack     │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key (or compatible LLM provider)

### 1. Clone and Configure

```bash
cd /path/to/sdlc-agent

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Start Infrastructure

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api worker
```

### 3. Access the System

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (admin/admin)
- **Health Check**: http://localhost:8000/health

## 📦 Project Structure

```
sdlc-agent/
├── src/sdlc_agent/
│   ├── agents/              # LangGraph agent implementations
│   │   ├── base.py         # Base agent class and state
│   │   ├── orchestrator.py # Main orchestrating agent
│   │   ├── developer.py    # Code implementation agent
│   │   └── graph.py        # LangGraph workflow definition
│   ├── api/
│   │   ├── routes/         # FastAPI route handlers
│   │   └── middleware.py   # Request/response middleware
│   ├── core/
│   │   ├── config.py       # Pydantic settings
│   │   ├── logging.py      # Structured logging
│   │   ├── telemetry.py    # OpenTelemetry setup
│   │   └── exceptions.py   # Exception hierarchy
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── engine.py       # Database connection
│   ├── main.py             # FastAPI application
│   └── worker.py           # Background task processor
├── frontend/                # Next.js application
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client, stores
│   │   └── hooks/          # Custom React hooks
│   └── package.json
├── docker/
│   ├── Dockerfile.api      # API container
│   ├── Dockerfile.worker   # Worker container
│   ├── Dockerfile.frontend # Frontend container
│   └── config/             # Service configurations
├── docker-compose.yml
├── pyproject.toml
└── alembic.ini
```

## 🤖 Agent Types

| Agent | Role | Capabilities |
|-------|------|-------------|
| **Orchestrator** | Workflow Coordination | Delegation, phase management, progress tracking |
| **Requirements** | Analysis | Extract requirements, create epics/stories |
| **Planning** | Architecture | Technical design, task breakdown |
| **Developer** | Implementation | Write code, modify files, create tests |
| **Code Review** | Quality | Review changes, suggest improvements |
| **Tester** | Testing | Generate tests, run test suites |
| **Security** | Security Analysis | Vulnerability scanning, SAST/DAST |
| **DevOps** | Deployment | CI/CD, infrastructure as code |

## 🔧 Configuration

### Environment Variables

```env
# LLM Provider
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.7

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sdlc_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
API_KEYS=key1,key2
```

### Pydantic Settings

All configuration is type-safe with Pydantic:

```python
from sdlc_agent.core.config import get_settings

settings = get_settings()
print(settings.llm.model)  # gpt-4-turbo-preview
print(settings.database.url)  # postgresql+asyncpg://...
```

## 📊 Observability

Full observability stack included:

- **Traces**: OpenTelemetry → Tempo → Grafana
- **Metrics**: OpenTelemetry → Prometheus → Grafana
- **Logs**: Structured JSON → Loki → Grafana

### Key Metrics

- `sdlc_requests_total` - HTTP requests count
- `sdlc_agent_execution_duration` - Agent execution time
- `sdlc_llm_tokens_total` - LLM token usage

## 🔐 Security Features

- **Authentication**: API key and JWT support
- **Authorization**: Role-based access control
- **Rate Limiting**: Per-IP request limiting
- **Audit Logging**: Full action audit trail
- **Secrets Management**: Environment-based secrets

## 🧪 Development

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Start infrastructure
docker compose up -d postgres redis qdrant

# Run API
uvicorn sdlc_agent.main:app --reload

# Run worker
python -m sdlc_agent.worker
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=sdlc_agent --cov-report=html
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## 📄 API Reference

### Projects

```http
POST /api/v1/projects
GET /api/v1/projects
GET /api/v1/projects/{id}
PATCH /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
```

### Workflows

```http
POST /api/v1/workflows
GET /api/v1/workflows
GET /api/v1/workflows/{id}
POST /api/v1/workflows/{id}/start
POST /api/v1/workflows/{id}/pause
POST /api/v1/workflows/{id}/resume
POST /api/v1/workflows/{id}/cancel
POST /api/v1/workflows/{id}/human-input/{input_id}
```

### Health

```http
GET /health
GET /health/ready
GET /health/live
```

## 🗺️ Roadmap

- [ ] **v0.2** - Additional agents (Architect, Planner, Reviewer)
- [ ] **v0.3** - GitHub/GitLab integration
- [ ] **v0.4** - Custom agent creation UI
- [ ] **v0.5** - Team collaboration features
- [ ] **v1.0** - Production hardening

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

---

Built with ❤️ using LangGraph, FastAPI, Next.js, and OpenAI
