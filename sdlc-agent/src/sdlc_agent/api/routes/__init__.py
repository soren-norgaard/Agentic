# =============================================================================
# SDLC Agent - API Routes
# =============================================================================

from fastapi import APIRouter

from sdlc_agent.api.routes import (
    audit,
    auth,
    github,
    health,
    permissions,
    projects,
    prs,
    roles,
    settings,
    stats,
    tasks,
    users,
    webhooks,
    workflows,
)

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(prs.router, prefix="/prs", tags=["Pull Requests"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# RBAC routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit Logs"])


