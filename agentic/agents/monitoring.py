"""Monitoring Agent - Sets up observability and monitoring."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import Phase, SDLCState


MONITORING_SYSTEM_PROMPT = """You are a Monitoring Agent specialized in observability and operational excellence.

Your responsibilities:
1. Design monitoring and alerting strategies
2. Configure application and infrastructure metrics
3. Set up logging aggregation and analysis
4. Define SLIs, SLOs, and error budgets
5. Create dashboards for key metrics
6. Configure alerting thresholds and escalation
7. Implement distributed tracing
8. Design runbooks for common incidents

Output your configuration in the following JSON format:
{
    "monitoring_config": {
        "metrics": [
            {
                "name": "http_request_duration_seconds",
                "type": "histogram",
                "description": "Request latency",
                "labels": ["method", "endpoint", "status"]
            }
        ],
        "slos": [
            {
                "name": "availability",
                "target": 99.9,
                "indicator": "successful_requests / total_requests"
            }
        ],
        "alerts": [
            {
                "name": "HighErrorRate",
                "condition": "error_rate > 5%",
                "severity": "critical",
                "runbook": "link/to/runbook"
            }
        ]
    },
    "infrastructure_files": [
        {
            "file_path": "monitoring/prometheus.yml",
            "content": "Prometheus configuration"
        }
    ],
    "dashboards": [
        {
            "name": "Application Overview",
            "description": "Key application metrics",
            "panels": ["Request Rate", "Error Rate", "Latency P99"]
        }
    ],
    "logging_config": {
        "format": "json",
        "level": "info",
        "aggregation": "elasticsearch"
    }
}

Observability Best Practices:
- Follow RED method (Rate, Errors, Duration) for services
- Follow USE method (Utilization, Saturation, Errors) for resources
- Implement structured logging
- Use correlation IDs for tracing
- Set actionable alerts (not noisy)
- Document runbooks for alerts
- Monitor both business and technical metrics"""


class MonitoringAgent(BaseAgent):
    """Agent for monitoring and observability setup."""

    def __init__(self):
        """Initialize the Monitoring Agent."""
        config = AgentConfig(
            name="MonitoringAgent",
            description="Configures monitoring, logging, and observability",
            phase=Phase.MONITORING,
            system_prompt=MONITORING_SYSTEM_PROMPT,
            temperature=0.3,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context for monitoring setup."""
        parts = []

        # System design
        if state.system_design:
            parts.append(f"## System Architecture\n{state.system_design[:1500]}...")

        # Deployment info
        if state.deployment_manifest:
            parts.append(
                f"\n## Deployment\n"
                f"- Environment: {state.deployment_manifest.environment}\n"
                f"- Version: {state.deployment_manifest.version}"
            )

        # NFRs
        if state.objective and state.objective.non_functional_requirements:
            parts.append(
                "\n## Non-Functional Requirements\n"
                + "\n".join(f"- {r}" for r in state.objective.non_functional_requirements)
            )

        # Endpoints to monitor (from architecture)
        parts.append("\n## Components to Monitor")
        for artifact in state.code_artifacts:
            if "test" not in artifact.file_path.lower() and artifact.language == "python":
                parts.append(f"- {artifact.file_path}")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the monitoring configuration response."""
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

            # Add monitoring infrastructure files
            from agentic.state.schemas import CodeArtifact

            for file_data in config.get("infrastructure_files", []):
                artifact = CodeArtifact(
                    file_path=file_data.get("file_path", ""),
                    content=file_data.get("content", ""),
                    language="yaml",
                )
                state.code_artifacts.append(artifact)

            monitoring_config = config.get("monitoring_config", {})
            metrics_count = len(monitoring_config.get("metrics", []))
            alerts_count = len(monitoring_config.get("alerts", []))
            slos_count = len(monitoring_config.get("slos", []))

            self.logger.info(
                "Monitoring configured",
                metrics=metrics_count,
                alerts=alerts_count,
                slos=slos_count,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse monitoring JSON", error=str(e))

        return state
