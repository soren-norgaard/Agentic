# =============================================================================
# SDLC Agent - DevOps Agent
# =============================================================================
# Handles deployment, CI/CD, and infrastructure.
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
class DevOpsState(AgentState):
    """State specific to the devops agent."""

    # DevOps artifacts
    pipeline_config: dict[str, Any] = field(default_factory=dict)
    infrastructure_config: dict[str, Any] = field(default_factory=dict)
    deployments: list[dict[str, Any]] = field(default_factory=list)
    environments: dict[str, dict[str, Any]] = field(default_factory=dict)


class DevOpsAgent(BaseAgent[DevOpsState]):
    """
    DevOps and deployment agent.

    Responsibilities:
    - Generate CI/CD pipeline configurations
    - Create Dockerfiles and container configs
    - Generate infrastructure as code
    - Manage deployments
    - Monitor deployment health
    """

    name = "devops"
    description = "Handles deployment, CI/CD, and infrastructure"
    phase = AgentPhase.DEPLOYMENT

    @property
    def system_prompt(self) -> str:
        return """You are a DevOps Engineer Agent specializing in CI/CD and infrastructure.

Your responsibilities:
1. Create CI/CD pipeline configurations (GitHub Actions, GitLab CI, etc.)
2. Generate Dockerfiles and docker-compose configurations
3. Create infrastructure as code (Terraform, Kubernetes manifests)
4. Manage deployment processes
5. Set up monitoring and alerting
6. Ensure deployment reliability and rollback capabilities

Best practices to follow:
- Use multi-stage Docker builds for smaller images
- Implement proper health checks
- Use environment variables for configuration
- Enable proper logging and metrics
- Implement zero-downtime deployments
- Set up proper resource limits

Consider security, scalability, and observability in all configurations."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_dockerfile",
                description="Generate a Dockerfile",
                parameters=[
                    ToolParameter(
                        name="service_name",
                        description="Name of the service",
                    ),
                    ToolParameter(
                        name="base_image",
                        description="Base Docker image to use",
                    ),
                    ToolParameter(
                        name="dockerfile_content",
                        description="The Dockerfile content",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_pipeline",
                description="Create a CI/CD pipeline configuration",
                parameters=[
                    ToolParameter(
                        name="platform",
                        description="CI/CD platform",
                        enum=["github_actions", "gitlab_ci", "jenkins", "azure_devops"],
                    ),
                    ToolParameter(
                        name="pipeline_name",
                        description="Name of the pipeline",
                    ),
                    ToolParameter(
                        name="config_content",
                        description="The pipeline configuration YAML",
                    ),
                ],
            ),
            ToolDefinition(
                name="create_k8s_manifest",
                description="Create Kubernetes manifest",
                parameters=[
                    ToolParameter(
                        name="resource_type",
                        description="Type of K8s resource",
                        enum=["deployment", "service", "configmap", "secret", "ingress"],
                    ),
                    ToolParameter(
                        name="manifest_content",
                        description="The K8s manifest YAML content",
                    ),
                ],
            ),
            ToolDefinition(
                name="deploy",
                description="Deploy to an environment",
                parameters=[
                    ToolParameter(
                        name="environment",
                        description="Target environment",
                        enum=["development", "staging", "production"],
                    ),
                    ToolParameter(
                        name="version",
                        description="Version/tag to deploy",
                    ),
                    ToolParameter(
                        name="strategy",
                        description="Deployment strategy",
                        enum=["rolling", "blue_green", "canary"],
                    ),
                ],
            ),
            ToolDefinition(
                name="request_deployment_approval",
                description="Request approval for production deployment",
                parameters=[
                    ToolParameter(
                        name="environment",
                        description="Target environment",
                    ),
                    ToolParameter(
                        name="changes_summary",
                        description="Summary of changes being deployed",
                    ),
                    ToolParameter(
                        name="risk_level",
                        description="Risk level of deployment",
                        enum=["low", "medium", "high"],
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_deployment",
                description="Mark deployment as complete",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Deployment summary",
                    ),
                    ToolParameter(
                        name="deployed_environments",
                        description="List of environments deployed to (JSON array)",
                    ),
                ],
            ),
        ]

    async def process(self, state: DevOpsState) -> DevOpsState:
        """Process DevOps tasks."""
        self.logger.info("DevOps agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Get project info from state or metadata
        project_info = state.metadata.get("project", {})
        objective = getattr(state, 'objective', '') or state.metadata.get('objective', '')
        code_files = getattr(state, 'code_files', {}) or {}
        
        state.add_message(
            MessageRole.USER,
            f"Please create deployment configurations for this project:\n\n"
            f"Project: {project_info.get('name', 'Unknown')}\n"
            f"Objective: {objective}\n"
            f"Files: {list(code_files.keys()) if code_files else 'Not specified'}\n\n"
            f"Create Dockerfile, CI/CD pipeline (GitHub Actions), and Kubernetes manifests.",
        )
        
        state = await self.run_with_tools(state)
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: DevOpsState,
    ) -> tuple[str, DevOpsState]:
        """Execute DevOps tools."""
        import json
        
        if tool_name == "create_dockerfile":
            state.infrastructure_config["dockerfile"] = {
                "service": tool_args.get("service_name"),
                "base_image": tool_args.get("base_image"),
                "content": tool_args.get("dockerfile_content"),
            }
            
            state.add_artifact(
                name="Dockerfile",
                artifact_type="dockerfile",
                content=tool_args.get("dockerfile_content"),
            )
            
            return f"Created Dockerfile for {tool_args.get('service_name')}", state
        
        elif tool_name == "create_pipeline":
            platform = tool_args.get("platform")
            state.pipeline_config = {
                "platform": platform,
                "name": tool_args.get("pipeline_name"),
                "content": tool_args.get("config_content"),
            }
            
            filename = {
                "github_actions": ".github/workflows/ci.yml",
                "gitlab_ci": ".gitlab-ci.yml",
                "jenkins": "Jenkinsfile",
                "azure_devops": "azure-pipelines.yml",
            }.get(platform, "pipeline.yml")
            
            state.add_artifact(
                name=filename,
                artifact_type="pipeline",
                content=tool_args.get("config_content"),
            )
            
            return f"Created {platform} pipeline: {tool_args.get('pipeline_name')}", state
        
        elif tool_name == "create_k8s_manifest":
            resource_type = tool_args.get("resource_type")
            
            if "kubernetes" not in state.infrastructure_config:
                state.infrastructure_config["kubernetes"] = []
            
            state.infrastructure_config["kubernetes"].append({
                "type": resource_type,
                "content": tool_args.get("manifest_content"),
            })
            
            state.add_artifact(
                name=f"k8s-{resource_type}.yaml",
                artifact_type="kubernetes",
                content=tool_args.get("manifest_content"),
            )
            
            return f"Created Kubernetes {resource_type} manifest", state
        
        elif tool_name == "deploy":
            env = tool_args.get("environment")
            deployment = {
                "environment": env,
                "version": tool_args.get("version"),
                "strategy": tool_args.get("strategy"),
                "status": "completed" if env != "production" else "pending_approval",
            }
            state.deployments.append(deployment)
            
            if env == "production":
                return f"Production deployment v{tool_args.get('version')} requires approval", state
            
            return f"Deployed v{tool_args.get('version')} to {env} ({tool_args.get('strategy')})", state
        
        elif tool_name == "request_deployment_approval":
            state.awaiting_human_input = True
            state.human_input_request = {
                "type": "deployment_approval",
                "environment": tool_args.get("environment"),
                "changes_summary": tool_args.get("changes_summary"),
                "risk_level": tool_args.get("risk_level"),
            }
            return f"Awaiting approval for {tool_args.get('environment')} deployment", state
        
        elif tool_name == "complete_deployment":
            envs = tool_args.get("deployed_environments", "[]")
            if isinstance(envs, str):
                try:
                    envs = json.loads(envs)
                except json.JSONDecodeError:
                    envs = []
            
            state.add_message(
                MessageRole.ASSISTANT,
                f"Deployment complete.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Deployed to: {', '.join(envs)}",
            )
            
            state.phase = AgentPhase.MONITORING
            return f"Deployment complete to {len(envs)} environments", state
        
        return f"Unknown tool: {tool_name}", state
