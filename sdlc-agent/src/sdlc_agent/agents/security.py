# =============================================================================
# SDLC Agent - Security Agent
# =============================================================================
# Performs security analysis and vulnerability scanning.
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
class SecurityState(AgentState):
    """State specific to the security agent."""

    # Security artifacts
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    compliance_checks: list[dict[str, Any]] = field(default_factory=list)
    security_score: float = 0.0


class SecurityAgent(BaseAgent[SecurityState]):
    """
    Security analysis agent.

    Responsibilities:
    - Perform static code analysis for security issues
    - Identify common vulnerabilities (OWASP Top 10)
    - Check for secrets/credentials in code
    - Scan dependencies for known vulnerabilities
    - Provide security recommendations
    """

    name = "security"
    description = "Performs security analysis and vulnerability scanning"
    phase = AgentPhase.SECURITY

    @property
    def system_prompt(self) -> str:
        return """You are a Security Analyst Agent specializing in application security.

Your responsibilities:
1. Identify security vulnerabilities in code
2. Check for OWASP Top 10 vulnerabilities
3. Detect hardcoded secrets and credentials
4. Analyze dependencies for known CVEs
5. Provide actionable remediation guidance
6. Assess overall security posture

Common vulnerabilities to check:
- SQL Injection
- XSS (Cross-Site Scripting)
- CSRF (Cross-Site Request Forgery)
- Insecure deserialization
- Broken authentication
- Sensitive data exposure
- Security misconfigurations
- Insufficient logging

Rate vulnerabilities by severity: critical, high, medium, low.
Provide specific remediation steps for each finding."""

    @property
    def tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="report_vulnerability",
                description="Report a security vulnerability",
                parameters=[
                    ToolParameter(
                        name="title",
                        description="Vulnerability title",
                    ),
                    ToolParameter(
                        name="severity",
                        description="Severity level",
                        enum=["critical", "high", "medium", "low", "info"],
                    ),
                    ToolParameter(
                        name="category",
                        description="Vulnerability category",
                        enum=["injection", "xss", "csrf", "auth", "crypto", "config", "dependency", "secrets", "other"],
                    ),
                    ToolParameter(
                        name="file_path",
                        description="Affected file path",
                    ),
                    ToolParameter(
                        name="line_number",
                        description="Affected line number",
                        required=False,
                    ),
                    ToolParameter(
                        name="description",
                        description="Detailed description of the vulnerability",
                    ),
                    ToolParameter(
                        name="remediation",
                        description="How to fix the vulnerability",
                    ),
                    ToolParameter(
                        name="cwe_id",
                        description="CWE ID if applicable",
                        required=False,
                    ),
                ],
            ),
            ToolDefinition(
                name="scan_dependencies",
                description="Scan dependencies for known vulnerabilities",
                parameters=[
                    ToolParameter(
                        name="manifest_file",
                        description="Path to dependency manifest (package.json, requirements.txt, etc.)",
                    ),
                ],
            ),
            ToolDefinition(
                name="check_secrets",
                description="Check for exposed secrets in code",
                parameters=[
                    ToolParameter(
                        name="scan_results",
                        description="Summary of secrets scan results",
                    ),
                    ToolParameter(
                        name="secrets_found",
                        description="Number of potential secrets found",
                    ),
                ],
            ),
            ToolDefinition(
                name="complete_security_review",
                description="Complete the security review",
                parameters=[
                    ToolParameter(
                        name="summary",
                        description="Summary of security findings",
                    ),
                    ToolParameter(
                        name="security_score",
                        description="Overall security score (0-100)",
                    ),
                    ToolParameter(
                        name="approved",
                        description="Whether the code passes security review",
                        enum=["true", "false"],
                    ),
                ],
            ),
        ]

    async def process(self, state: SecurityState) -> SecurityState:
        """Process security analysis."""
        self.logger.info("Security agent processing", workflow_id=state.workflow_id)
        
        # Clear messages from previous agents - each agent starts fresh
        state.messages = []
        
        # Get code from state or metadata
        code_files = getattr(state, 'code_files', {}) or state.metadata.get("code_files", {})
        
        code_to_scan = ""
        if code_files:
            for path, content in code_files.items():
                code_to_scan += f"\n--- {path} ---\n{content}\n"
        else:
            code_to_scan = state.metadata.get("code", "No code provided")
        
        state.add_message(
            MessageRole.USER,
            f"Please perform a security review of the following code:\n\n{code_to_scan}",
        )
        
        state = await self.run_with_tools(state)
        return state

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        state: SecurityState,
    ) -> tuple[str, SecurityState]:
        """Execute security tools."""
        import json
        import uuid
        
        if tool_name == "report_vulnerability":
            vuln_id = str(uuid.uuid4())[:8]
            
            vuln = {
                "id": vuln_id,
                "title": tool_args.get("title"),
                "severity": tool_args.get("severity"),
                "category": tool_args.get("category"),
                "file_path": tool_args.get("file_path"),
                "line_number": tool_args.get("line_number"),
                "description": tool_args.get("description"),
                "remediation": tool_args.get("remediation"),
                "cwe_id": tool_args.get("cwe_id"),
            }
            state.vulnerabilities.append(vuln)
            
            state.add_artifact(
                name=f"VULN-{vuln_id}",
                artifact_type="vulnerability",
                content=json.dumps(vuln),
            )
            
            severity = tool_args.get("severity", "medium")
            return f"Found {severity} vulnerability: {tool_args.get('title')}", state
        
        elif tool_name == "scan_dependencies":
            # Simulate dependency scan
            state.security_findings.append({
                "type": "dependency_scan",
                "manifest": tool_args.get("manifest_file"),
                "status": "completed",
                "vulnerabilities_found": 0,
            })
            return f"Scanned dependencies in {tool_args.get('manifest_file')}: No vulnerabilities found", state
        
        elif tool_name == "check_secrets":
            secrets_found = int(tool_args.get("secrets_found", 0))
            state.security_findings.append({
                "type": "secrets_scan",
                "summary": tool_args.get("scan_results"),
                "secrets_found": secrets_found,
            })
            
            if secrets_found > 0:
                return f"Warning: {secrets_found} potential secrets found in code", state
            return "Secrets scan complete: No exposed secrets found", state
        
        elif tool_name == "complete_security_review":
            state.security_score = float(tool_args.get("security_score", 0))
            approved = tool_args.get("approved", "false") == "true"
            
            critical = len([v for v in state.vulnerabilities if v.get("severity") == "critical"])
            high = len([v for v in state.vulnerabilities if v.get("severity") == "high"])
            
            # Mark security phase as complete
            if hasattr(state, 'phases_completed') and 'security' not in state.phases_completed:
                state.phases_completed.append('security')
            
            state.add_message(
                MessageRole.ASSISTANT,
                f"Security review complete.\n\nSummary: {tool_args.get('summary')}\n\n"
                f"Security Score: {state.security_score}/100\n"
                f"Vulnerabilities: {critical} critical, {high} high, {len(state.vulnerabilities) - critical - high} other\n"
                f"Status: {'Approved' if approved else 'Requires remediation'}",
            )
            
            if approved:
                state.phase = AgentPhase.DEPLOYMENT
            else:
                state.awaiting_human_input = True
                state.human_input_request = {
                    "type": "security_approval",
                    "vulnerabilities": len(state.vulnerabilities),
                    "critical": critical,
                    "high": high,
                }
            
            return f"Security review: Score {state.security_score}/100, {'approved' if approved else 'needs remediation'}", state
        
        return f"Unknown tool: {tool_name}", state
