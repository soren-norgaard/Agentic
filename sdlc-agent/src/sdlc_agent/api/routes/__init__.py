# =============================================================================
# SDLC Agent - API Routes
# =============================================================================

from fastapi import APIRouter

from sdlc_agent.api.routes import health, projects, workflows

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
