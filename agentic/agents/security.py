"""Security Agent - Performs security analysis."""

import json
from langchain_core.messages import AIMessage

from agentic.agents.base import AgentConfig, BaseAgent
from agentic.state.schemas import Phase, SDLCState, SecurityFinding, Severity


SECURITY_SYSTEM_PROMPT = """You are a Security Agent specialized in identifying security vulnerabilities and risks.

Your responsibilities:
1. Perform static application security testing (SAST)
2. Identify common vulnerability patterns (OWASP Top 10)
3. Check for hardcoded secrets and sensitive data exposure
4. Analyze authentication and authorization implementations
5. Review input validation and output encoding
6. Identify insecure dependencies
7. Check for security misconfigurations
8. Provide remediation recommendations

Output your analysis in the following JSON format:
{
    "overall_risk_level": "critical|high|medium|low",
    "findings": [
        {
            "title": "SQL Injection Vulnerability",
            "description": "Detailed description of the vulnerability",
            "severity": "critical|high|medium|low|info",
            "file_path": "path/to/vulnerable/file.py",
            "line_number": 42,
            "cwe_id": "CWE-89",
            "remediation": "How to fix this vulnerability",
            "code_snippet": "The vulnerable code"
        }
    ],
    "security_approved": true/false,
    "blocking_issues": ["List of issues that must be fixed before deployment"],
    "recommendations": ["General security recommendations"]
}

Security Focus Areas:
- Injection flaws (SQL, NoSQL, Command, LDAP)
- Broken authentication/session management
- Sensitive data exposure
- XML External Entities (XXE)
- Broken access control
- Security misconfiguration
- Cross-Site Scripting (XSS)
- Insecure deserialization
- Using components with known vulnerabilities
- Insufficient logging and monitoring"""


class SecurityAgent(BaseAgent):
    """Agent for security analysis."""

    def __init__(self):
        """Initialize the Security Agent."""
        config = AgentConfig(
            name="SecurityAgent",
            description="Performs security analysis and vulnerability detection",
            phase=Phase.SECURITY,
            system_prompt=SECURITY_SYSTEM_PROMPT,
            temperature=0.2,
        )
        super().__init__(config)

    def _build_context(self, state: SDLCState) -> str:
        """Build context with code to analyze."""
        parts = ["## Code for Security Review"]

        for artifact in state.code_artifacts:
            parts.append(f"\n### {artifact.file_path}\n```{artifact.language}")
            parts.append(artifact.content)
            parts.append("```")

        # Include architecture for context
        if state.system_design:
            parts.append(f"\n## System Architecture\n{state.system_design[:1500]}...")

        return "\n\n".join(parts)

    def _process_response(self, response: AIMessage, state: SDLCState) -> SDLCState:
        """Process the security analysis response."""
        try:
            content = response.content
            if isinstance(content, str):
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                analysis = json.loads(content.strip())
            else:
                analysis = {}

            # Create security findings
            for finding_data in analysis.get("findings", []):
                severity_str = finding_data.get("severity", "info").lower()
                try:
                    severity = Severity(severity_str)
                except ValueError:
                    severity = Severity.INFO

                finding = SecurityFinding(
                    title=finding_data.get("title", "Unknown Finding"),
                    description=finding_data.get("description", ""),
                    severity=severity,
                    file_path=finding_data.get("file_path"),
                    line_number=finding_data.get("line_number"),
                    cwe_id=finding_data.get("cwe_id"),
                    remediation=finding_data.get("remediation"),
                )
                state.security_findings.append(finding)

            # Update security approval
            state.security_approved = analysis.get("security_approved", False)

            critical_count = sum(
                1 for f in state.security_findings if f.severity == Severity.CRITICAL
            )
            high_count = sum(
                1 for f in state.security_findings if f.severity == Severity.HIGH
            )

            self.logger.info(
                "Security analysis completed",
                total_findings=len(state.security_findings),
                critical=critical_count,
                high=high_count,
                approved=state.security_approved,
            )

        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse security JSON", error=str(e))

        return state
