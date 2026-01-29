"""DevOps Agent - Handles deployment and infrastructure."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import DeploymentManifest, Phase, SDLCState


DEVOPS_SYSTEM_PROMPT = """You are a DevOps Agent specialized in deployment, CI/CD, and infrastructure.

Your responsibilities:
1. Create deployment configurations (Docker, Kubernetes, etc.)
2. Design CI/CD pipelines
3. Configure infrastructure as code
4. Set up environment configurations
5. Define deployment strategies (rolling, blue-green, canary)
6. Configure monitoring and logging infrastructure
7. Implement security best practices in deployment

Output your configuration in the following JSON format:
{
    "deployment_manifest": {
        "environment": "dev|staging|prod",
        "version": "1.0.0",
        "artifacts": ["list of files/images to deploy"],
        "config": {
            "replicas": 3,
            "resources": {"cpu": "500m", "memory": "512Mi"},
            "env_vars": {"KEY": "value"}
        }
    },
    "infrastructure_files": [
        {
            "file_path": "docker/Dockerfile",
            "content": "Dockerfile content",
            "description": "What this file configures"
        }
    ],
    "ci_cd_pipeline": {
        "file_path": ".github/workflows/deploy.yml",
        "content": "Pipeline configuration"
    },
    "deployment_notes": "Notes about the deployment process"
}

DevOps Best Practices:
- Use immutable infrastructure
- Implement health checks and readiness probes
- Configure proper resource limits
- Use secrets management (not hardcoded)
- Implement proper logging and monitoring
- Design for zero-downtime deployments
- Include rollback procedures"""


class DevOpsAgent(BaseAgent):
    """Agent for deployment and infrastructure."""

    def __init__(self):
        """Initialize the DevOps Agent."""
        config = AgentConfig(
            name="DevOpsAgent",
            description="Handles deployment, CI/CD, and infrastructure configuration",
            phase=Phase.DEPLOYMENT,
            system_prompt=DEVOPS_SYSTEM_PROMPT,
            temperature=0.3,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context for deployment."""
        parts = []

        # Project info
        parts.append(f"## Project: {state.project_name}")

        # Architecture
        if state.system_design:
            parts.append(f"\n## System Architecture\n{state.system_design[:1500]}...")

        # Code artifacts to deploy
        parts.append("\n## Code Artifacts")
        for artifact in state.code_artifacts:
            if "test" not in artifact.file_path.lower():
                parts.append(f"- {artifact.file_path} ({artifact.language})")

        # Non-functional requirements
        if state.objective and state.objective.non_functional_requirements:
            parts.append(
                "\n## Non-Functional Requirements\n"
                + "\n".join(f"- {r}" for r in state.objective.non_functional_requirements)
            )

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the deployment configuration response."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                config = json.loads(content.strip())
            else:
                config = {}

            # Create deployment manifest
            manifest_data = config.get("deployment_manifest", {})
            state.deployment_manifest = DeploymentManifest(
                environment=manifest_data.get("environment", "dev"),
                version=manifest_data.get("version", "0.1.0"),
                artifacts=manifest_data.get("artifacts", []),
                config=manifest_data.get("config", {}),
            )

            # Add infrastructure files as artifacts
            from agentic.state.schemas import CodeArtifact

            for file_data in config.get("infrastructure_files", []):
                artifact = CodeArtifact(
                    file_path=file_data.get("file_path", ""),
                    content=file_data.get("content", ""),
                    language="yaml" if file_data.get("file_path", "").endswith((".yml", ".yaml")) else "dockerfile",
                )
                state.code_artifacts.append(artifact)

            # Add CI/CD pipeline
            ci_cd = config.get("ci_cd_pipeline")
            if ci_cd:
                artifact = CodeArtifact(
                    file_path=ci_cd.get("file_path", ".github/workflows/ci.yml"),
                    content=ci_cd.get("content", ""),
                    language="yaml",
                )
                state.code_artifacts.append(artifact)

            self.logger.info(
                "Deployment configured",
                environment=state.deployment_manifest.environment,
                version=state.deployment_manifest.version,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse devops JSON", error=str(e))

        return state
