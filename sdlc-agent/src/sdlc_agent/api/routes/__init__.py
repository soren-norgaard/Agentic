# =============================================================================
# SDLC Agent - API Routes
# =============================================================================

from fastapi import APIRouter

from sdlc_agent.api.routes import github, health, projects, stats, tasks, workflows

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub"])

