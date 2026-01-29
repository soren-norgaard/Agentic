# SDLC Agent - Production Roadmap

## 🎉 Current Status: System Running Locally

All services are now operational:

| Service | Status | URL |
|---------|--------|-----|
| **Frontend** | ✅ Running | http://localhost:3000 |
| **API** | ✅ Healthy | http://localhost:8000/api/v1/health |
| **Workers** | ✅ Running (2 replicas) | - |
| **PostgreSQL** | ✅ Healthy | localhost:5432 |
| **Redis** | ✅ Healthy | localhost:6379 |
| **Qdrant** | ✅ Running | localhost:6333 |
| **MinIO** | ✅ Healthy | localhost:9000/9001 |
| **Grafana** | ✅ Running | http://localhost:3001 |
| **Prometheus** | ✅ Running | http://localhost:9090 |
| **Tempo** | ✅ Running | localhost:3200 |
| **Loki** | ✅ Running | localhost:3100 |
| **OTel Collector** | ✅ Running | localhost:4317/4318 |

---

## Phase 1: LLM Integration (Immediate)

### 1.1 Configure OpenAI / Azure OpenAI
```bash
# Edit .env file with your API keys
OPENAI_API_KEY=sk-...
# OR for Azure:
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

### 1.2 Test LLM Connectivity
```bash
# Restart API to pick up new keys
docker compose restart api worker

# Test via API
curl http://localhost:8000/api/v1/health/ready
```

### 1.3 Configure Agent Models
Edit `src/sdlc_agent/agents/config.py` to set models per agent:
- **Orchestrator**: GPT-4o (reasoning)
- **Developer**: GPT-4o or Claude 3.5 (code generation)
- **Reviewer**: GPT-4o (analysis)
- **Tester**: GPT-4o (test generation)

---

## Phase 2: Database Migrations

### 2.1 Run Initial Migrations
```bash
# Enter API container
docker exec -it sdlc-api bash

# Run Alembic migrations
alembic upgrade head
```

### 2.2 Seed Initial Data
```bash
# Create default organization and user
python -m sdlc_agent.scripts.seed_data
```

---

## Phase 3: Agent Workflow Configuration

### 3.1 Configure LangGraph Workflows
- Define state machines in `src/sdlc_agent/agents/graphs/`
- Configure checkpointing for workflow persistence
- Set up human-in-the-loop breakpoints

### 3.2 Vector Memory Setup
```bash
# Initialize Qdrant collections
curl -X PUT http://localhost:6333/collections/agent_memory \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
```

### 3.3 Agent Tool Configuration
- Enable/disable tools per agent type
- Configure rate limits for external APIs
- Set up sandbox environments for code execution

---

## Phase 4: Authentication & Security

### 4.1 Enable JWT Authentication
```bash
# Generate JWT secret
openssl rand -base64 32

# Update .env
JWT_SECRET_KEY=<generated-secret>
JWT_ALGORITHM=HS256
```

### 4.2 Configure API Keys
```bash
# Enable API key auth for integrations
API_KEY_ENABLED=true
```

### 4.3 OAuth2 Setup (Optional)
```bash
# For enterprise SSO
OAUTH2_ENABLED=true
OAUTH2_PROVIDER=okta
OAUTH2_CLIENT_ID=...
OAUTH2_CLIENT_SECRET=...
OAUTH2_ISSUER_URL=https://your-org.okta.com
```

---

## Phase 5: Observability Enhancement

### 5.1 Configure Grafana Dashboards
1. Open http://localhost:3001 (admin/admin)
2. Add data sources:
   - Prometheus: http://prometheus:9090
   - Loki: http://loki:3100
   - Tempo: http://tempo:3200
3. Import dashboards from `docker/config/grafana/dashboards/`

### 5.2 Set Up Alerts
- Configure Prometheus alerting rules
- Set up PagerDuty/Slack integrations
- Define SLOs for agent response times

### 5.3 Enable Sentry (Optional)
```bash
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production
```

---

## Phase 6: Production Deployment

### 6.1 Kubernetes Manifests
Create Helm charts or Kustomize overlays:
```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
├── overlays/
│   ├── staging/
│   └── production/
└── helm/
    └── sdlc-agent/
```

### 6.2 Infrastructure Requirements
| Component | Production Spec |
|-----------|-----------------|
| API | 2+ replicas, 2 CPU, 4GB RAM |
| Workers | 4+ replicas, 4 CPU, 8GB RAM |
| PostgreSQL | RDS/Cloud SQL, Multi-AZ |
| Redis | ElastiCache/Memorystore |
| Qdrant | Managed or self-hosted cluster |

### 6.3 CI/CD Pipeline
```yaml
# GitHub Actions example
name: Deploy SDLC Agent
on:
  push:
    branches: [main]
jobs:
  build:
    - Build Docker images
    - Push to registry
    - Deploy to Kubernetes
  test:
    - Run integration tests
    - Security scanning
```

### 6.4 Secrets Management
- AWS Secrets Manager / HashiCorp Vault
- Kubernetes Secrets with external-secrets operator
- Environment-specific configurations

---

## Phase 7: Enterprise Features

### 7.1 Multi-Tenancy
- Organization isolation
- Per-tenant rate limiting
- Tenant-specific LLM configurations

### 7.2 Audit Logging
- Comprehensive action logging
- Compliance reporting (SOC2, GDPR)
- Data retention policies

### 7.3 RBAC
- Role-based access control
- Custom permission sets
- Team management

### 7.4 Advanced Integrations
- GitHub/GitLab webhooks
- Jira/Linear issue tracking
- Slack/Teams notifications
- Custom tool integrations

---

## Quick Start Checklist

- [ ] Set OpenAI/Azure API keys in `.env`
- [ ] Run database migrations
- [ ] Configure JWT authentication
- [ ] Test agent workflows via API
- [ ] Import Grafana dashboards
- [ ] Create first project via UI
- [ ] Run end-to-end workflow test

---

## Support & Documentation

- **API Docs**: http://localhost:8000/docs (dev mode)
- **Architecture**: See `docs/architecture.md`
- **Agent Guide**: See `docs/agents.md`
