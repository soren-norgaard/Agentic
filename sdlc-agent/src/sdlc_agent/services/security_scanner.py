# =============================================================================
# SDLC Agent - Security Scanner Service
# =============================================================================
# Integrates Bandit, Semgrep, and pip-audit for comprehensive security scanning.
# Runs SAST analysis on PR code and reports findings to GitHub.
# =============================================================================

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================

class Severity(str, Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of security findings."""
    INJECTION = "injection"
    XSS = "xss"
    SECRETS = "secrets"
    CRYPTO = "crypto"
    AUTH = "auth"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    CODE_QUALITY = "code_quality"
    OTHER = "other"


@dataclass
class SecurityFinding:
    """A single security finding."""
    id: str
    severity: Severity
    category: FindingCategory
    title: str
    description: str
    file_path: str
    line_number: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None
    cwe_id: str | None = None
    tool: str = "unknown"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
            "tool": self.tool,
        }


@dataclass
class DependencyVulnerability:
    """A vulnerable dependency finding."""
    package: str
    installed_version: str
    fixed_version: str | None
    vulnerability_id: str
    severity: Severity
    description: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "installed_version": self.installed_version,
            "fixed_version": self.fixed_version,
            "vulnerability_id": self.vulnerability_id,
            "severity": self.severity.value,
            "description": self.description,
        }


@dataclass
class SecurityScanResult:
    """Complete security scan result."""
    success: bool
    scan_duration_ms: int
    files_scanned: int
    
    # Findings by source
    sast_findings: list[SecurityFinding] = field(default_factory=list)
    dependency_vulnerabilities: list[DependencyVulnerability] = field(default_factory=list)
    
    # Aggregated counts
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Gate decision
    passed: bool = True
    blocking_issues: list[str] = field(default_factory=list)
    
    # Score 0-100
    security_score: float = 100.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "scan_duration_ms": self.scan_duration_ms,
            "files_scanned": self.files_scanned,
            "sast_findings": [f.to_dict() for f in self.sast_findings],
            "dependency_vulnerabilities": [v.to_dict() for v in self.dependency_vulnerabilities],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "passed": self.passed,
            "blocking_issues": self.blocking_issues,
            "security_score": self.security_score,
        }
    
    def to_markdown(self) -> str:
        """Convert to Markdown for GitHub comment."""
        status_emoji = "✅" if self.passed else "❌"
        lines = [
            f"## {status_emoji} Security Scan Results",
            "",
            f"**Security Score:** {self.security_score:.0f}/100",
            f"**Files Scanned:** {self.files_scanned}",
            f"**Scan Duration:** {self.scan_duration_ms}ms",
            "",
        ]
        
        # Summary table
        if self.critical_count or self.high_count or self.medium_count or self.low_count:
            lines.extend([
                "### Findings Summary",
                "",
                "| Severity | Count |",
                "|----------|-------|",
                f"| 🔴 Critical | {self.critical_count} |",
                f"| 🟠 High | {self.high_count} |",
                f"| 🟡 Medium | {self.medium_count} |",
                f"| 🔵 Low | {self.low_count} |",
                "",
            ])
        else:
            lines.extend([
                "### ✨ No security issues found!",
                "",
            ])
        
        # Blocking issues
        if self.blocking_issues:
            lines.extend([
                "### ⛔ Blocking Issues (must fix before merge)",
                "",
            ])
            for issue in self.blocking_issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        # SAST Findings (group by severity)
        if self.sast_findings:
            lines.extend([
                "### 🔍 Static Analysis Findings",
                "",
            ])
            
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                findings = [f for f in self.sast_findings if f.severity == severity]
                if findings:
                    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}[severity.value]
                    lines.append(f"#### {emoji} {severity.value.title()}")
                    lines.append("")
                    for f in findings[:5]:  # Limit to 5 per severity
                        lines.append(f"- **{f.title}** in `{f.file_path}`:{f.line_number or '?'}")
                        lines.append(f"  - {f.description}")
                        if f.remediation:
                            lines.append(f"  - 💡 Fix: {f.remediation}")
                    if len(findings) > 5:
                        lines.append(f"  - ... and {len(findings) - 5} more")
                    lines.append("")
        
        # Dependency vulnerabilities
        if self.dependency_vulnerabilities:
            lines.extend([
                "### 📦 Vulnerable Dependencies",
                "",
                "| Package | Version | Vulnerability | Fix |",
                "|---------|---------|---------------|-----|",
            ])
            for v in self.dependency_vulnerabilities[:10]:
                fix = v.fixed_version or "No fix available"
                lines.append(f"| `{v.package}` | {v.installed_version} | {v.vulnerability_id} | {fix} |")
            if len(self.dependency_vulnerabilities) > 10:
                lines.append(f"| ... | ... | +{len(self.dependency_vulnerabilities) - 10} more | ... |")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# Security Scanner Service
# =============================================================================

class SecurityScanner:
    """
    Comprehensive security scanner integrating multiple tools.
    
    Tools:
    - Bandit: Python-specific security linter
    - Semgrep: Multi-language SAST with OWASP rules
    - pip-audit: Python dependency vulnerability scanner
    """
    
    def __init__(self, repo_path: str | Path | None = None):
        """
        Initialize security scanner.
        
        Args:
            repo_path: Path to repository root. If None, uses current directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.logger = logger.bind(service="security_scanner")
    
    async def scan(
        self,
        files: list[dict[str, Any]] | None = None,
        include_dependencies: bool = True,
    ) -> SecurityScanResult:
        """
        Run full security scan.
        
        Args:
            files: Optional list of files to scan (from PR diff).
                   If None, scans entire repository.
            include_dependencies: Whether to run dependency audit.
        
        Returns:
            Complete scan results.
        """
        import time
        start_time = time.time()
        
        all_findings: list[SecurityFinding] = []
        dep_vulns: list[DependencyVulnerability] = []
        files_scanned = 0
        
        try:
            # Run scans in parallel
            tasks = [
                self._run_bandit(files),
                self._run_semgrep(files),
            ]
            
            if include_dependencies:
                tasks.append(self._run_pip_audit())
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process Bandit results
            if not isinstance(results[0], Exception):
                bandit_findings, bandit_files = results[0]
                all_findings.extend(bandit_findings)
                files_scanned += bandit_files
            else:
                self.logger.warning("Bandit scan failed", error=str(results[0]))
            
            # Process Semgrep results
            if not isinstance(results[1], Exception):
                semgrep_findings, semgrep_files = results[1]
                all_findings.extend(semgrep_findings)
                files_scanned = max(files_scanned, semgrep_files)
            else:
                self.logger.warning("Semgrep scan failed", error=str(results[1]))
            
            # Process pip-audit results
            if include_dependencies and len(results) > 2:
                if not isinstance(results[2], Exception):
                    dep_vulns = results[2]
                else:
                    self.logger.warning("pip-audit failed", error=str(results[2]))
            
        except Exception as e:
            self.logger.error("Security scan failed", error=str(e))
            return SecurityScanResult(
                success=False,
                scan_duration_ms=int((time.time() - start_time) * 1000),
                files_scanned=0,
            )
        
        # Calculate counts
        critical = len([f for f in all_findings if f.severity == Severity.CRITICAL])
        high = len([f for f in all_findings if f.severity == Severity.HIGH])
        medium = len([f for f in all_findings if f.severity == Severity.MEDIUM])
        low = len([f for f in all_findings if f.severity == Severity.LOW])
        
        # Add critical deps
        critical += len([v for v in dep_vulns if v.severity == Severity.CRITICAL])
        high += len([v for v in dep_vulns if v.severity == Severity.HIGH])
        
        # Calculate score (100 - penalties)
        score = 100.0
        score -= critical * 25  # -25 per critical
        score -= high * 10      # -10 per high
        score -= medium * 3     # -3 per medium
        score -= low * 1        # -1 per low
        score = max(0, score)
        
        # Determine blocking issues
        blocking = []
        if critical > 0:
            blocking.append(f"{critical} critical vulnerability(ies) found")
        if high > 0:
            blocking.append(f"{high} high severity issue(s) found")
        
        # Gate decision
        passed = len(blocking) == 0
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.logger.info(
            "Security scan complete",
            files_scanned=files_scanned,
            findings=len(all_findings),
            dep_vulns=len(dep_vulns),
            passed=passed,
            score=score,
            duration_ms=duration_ms,
        )
        
        return SecurityScanResult(
            success=True,
            scan_duration_ms=duration_ms,
            files_scanned=files_scanned,
            sast_findings=all_findings,
            dependency_vulnerabilities=dep_vulns,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            passed=passed,
            blocking_issues=blocking,
            security_score=score,
        )
    
    async def _run_bandit(
        self,
        files: list[dict[str, Any]] | None = None,
    ) -> tuple[list[SecurityFinding], int]:
        """Run Bandit security linter on Python files."""
        findings = []
        files_scanned = 0
        
        try:
            # Determine what to scan
            if files:
                # Scan specific files from PR
                python_files = [
                    f["filename"] for f in files
                    if f.get("filename", "").endswith(".py")
                ]
                if not python_files:
                    return [], 0
                
                # Write files to temp directory for scanning
                with tempfile.TemporaryDirectory() as tmpdir:
                    for f in files:
                        if not f.get("filename", "").endswith(".py"):
                            continue
                        filepath = Path(tmpdir) / f["filename"]
                        filepath.parent.mkdir(parents=True, exist_ok=True)
                        # Get file content from patch or fetch
                        content = f.get("content", "")
                        if content:
                            filepath.write_text(content)
                            files_scanned += 1
                    
                    if files_scanned == 0:
                        return [], 0
                    
                    result = await self._run_command([
                        "bandit",
                        "-r", tmpdir,
                        "-f", "json",
                        "-ll",  # Only medium and above
                    ])
            else:
                # Scan entire repo
                result = await self._run_command([
                    "bandit",
                    "-r", str(self.repo_path / "src"),
                    "-f", "json",
                    "-ll",
                ])
            
            if result.returncode not in (0, 1):  # 1 means issues found
                self.logger.warning("Bandit returned error", returncode=result.returncode)
                return [], 0
            
            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return [], 0
            
            files_scanned = data.get("metrics", {}).get("_totals", {}).get("loc", 0) // 20  # Estimate
            
            for issue in data.get("results", []):
                severity = self._map_bandit_severity(issue.get("issue_severity", "LOW"))
                
                findings.append(SecurityFinding(
                    id=f"bandit-{issue.get('test_id', 'unknown')}",
                    severity=severity,
                    category=self._map_bandit_category(issue.get("test_id", "")),
                    title=issue.get("test_name", "Unknown Issue"),
                    description=issue.get("issue_text", ""),
                    file_path=issue.get("filename", ""),
                    line_number=issue.get("line_number"),
                    line_end=issue.get("line_range", [None])[-1],
                    code_snippet=issue.get("code", ""),
                    cwe_id=issue.get("issue_cwe", {}).get("id"),
                    tool="bandit",
                ))
        
        except FileNotFoundError:
            self.logger.warning("Bandit not installed, skipping")
        except Exception as e:
            self.logger.error("Bandit scan error", error=str(e))
        
        return findings, files_scanned
    
    async def _run_semgrep(
        self,
        files: list[dict[str, Any]] | None = None,
    ) -> tuple[list[SecurityFinding], int]:
        """Run Semgrep with security rules."""
        findings = []
        files_scanned = 0
        
        try:
            cmd = [
                "semgrep",
                "--config", "p/security-audit",
                "--config", "p/owasp-top-ten",
                "--json",
                "--quiet",
            ]
            
            if files:
                # Scan specific files
                python_files = [
                    f["filename"] for f in files
                    if f.get("filename", "").endswith((".py", ".js", ".ts", ".jsx", ".tsx"))
                ]
                if not python_files:
                    return [], 0
                cmd.extend(python_files)
            else:
                cmd.append(str(self.repo_path / "src"))
            
            result = await self._run_command(cmd, cwd=str(self.repo_path))
            
            if result.returncode not in (0, 1):
                self.logger.warning("Semgrep returned error", returncode=result.returncode)
                return [], 0
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return [], 0
            
            files_scanned = len(data.get("paths", {}).get("scanned", []))
            
            for match in data.get("results", []):
                severity = self._map_semgrep_severity(
                    match.get("extra", {}).get("severity", "INFO")
                )
                
                findings.append(SecurityFinding(
                    id=f"semgrep-{match.get('check_id', 'unknown')}",
                    severity=severity,
                    category=self._map_semgrep_category(match.get("check_id", "")),
                    title=match.get("check_id", "Unknown").split(".")[-1].replace("-", " ").title(),
                    description=match.get("extra", {}).get("message", ""),
                    file_path=match.get("path", ""),
                    line_number=match.get("start", {}).get("line"),
                    line_end=match.get("end", {}).get("line"),
                    code_snippet=match.get("extra", {}).get("lines", ""),
                    remediation=match.get("extra", {}).get("fix", None),
                    cwe_id=match.get("extra", {}).get("metadata", {}).get("cwe"),
                    tool="semgrep",
                ))
        
        except FileNotFoundError:
            self.logger.warning("Semgrep not installed, skipping")
        except Exception as e:
            self.logger.error("Semgrep scan error", error=str(e))
        
        return findings, files_scanned
    
    async def _run_pip_audit(self) -> list[DependencyVulnerability]:
        """Run pip-audit for dependency vulnerabilities."""
        vulns = []
        
        try:
            # Check for requirements.txt or pyproject.toml
            req_file = self.repo_path / "requirements.txt"
            pyproject = self.repo_path / "pyproject.toml"
            
            cmd = ["pip-audit", "--format", "json"]
            
            if req_file.exists():
                cmd.extend(["-r", str(req_file)])
            elif pyproject.exists():
                cmd.append(str(self.repo_path))
            else:
                return []
            
            result = await self._run_command(cmd, cwd=str(self.repo_path))
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return []
            
            for entry in data.get("dependencies", []):
                for vuln in entry.get("vulns", []):
                    severity = self._map_pip_audit_severity(vuln.get("id", ""))
                    
                    vulns.append(DependencyVulnerability(
                        package=entry.get("name", ""),
                        installed_version=entry.get("version", ""),
                        fixed_version=vuln.get("fix_versions", [None])[0] if vuln.get("fix_versions") else None,
                        vulnerability_id=vuln.get("id", ""),
                        severity=severity,
                        description=vuln.get("description", ""),
                    ))
        
        except FileNotFoundError:
            self.logger.warning("pip-audit not installed, skipping")
        except Exception as e:
            self.logger.error("pip-audit error", error=str(e))
        
        return vulns
    
    async def _run_command(
        self,
        cmd: list[str],
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a command asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode or 0,
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else "",
        )
    
    def _map_bandit_severity(self, severity: str) -> Severity:
        """Map Bandit severity to our enum."""
        mapping = {
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
        }
        return mapping.get(severity.upper(), Severity.INFO)
    
    def _map_bandit_category(self, test_id: str) -> FindingCategory:
        """Map Bandit test ID to category."""
        if test_id.startswith("B1"):  # B1xx - misc tests
            return FindingCategory.CODE_QUALITY
        elif test_id.startswith("B2"):  # B2xx - blacklist calls
            return FindingCategory.INJECTION
        elif test_id.startswith("B3"):  # B3xx - blacklist imports
            return FindingCategory.CONFIG
        elif test_id.startswith("B4"):  # B4xx - hardcoded
            return FindingCategory.SECRETS
        elif test_id.startswith("B5"):  # B5xx - cryptography
            return FindingCategory.CRYPTO
        elif test_id.startswith("B6"):  # B6xx - yaml
            return FindingCategory.CONFIG
        return FindingCategory.OTHER
    
    def _map_semgrep_severity(self, severity: str) -> Severity:
        """Map Semgrep severity to our enum."""
        mapping = {
            "ERROR": Severity.HIGH,
            "WARNING": Severity.MEDIUM,
            "INFO": Severity.LOW,
        }
        return mapping.get(severity.upper(), Severity.INFO)
    
    def _map_semgrep_category(self, check_id: str) -> FindingCategory:
        """Map Semgrep check ID to category."""
        check_lower = check_id.lower()
        if "injection" in check_lower or "sqli" in check_lower:
            return FindingCategory.INJECTION
        elif "xss" in check_lower:
            return FindingCategory.XSS
        elif "secret" in check_lower or "credential" in check_lower or "password" in check_lower:
            return FindingCategory.SECRETS
        elif "crypto" in check_lower or "hash" in check_lower:
            return FindingCategory.CRYPTO
        elif "auth" in check_lower:
            return FindingCategory.AUTH
        return FindingCategory.OTHER
    
    def _map_pip_audit_severity(self, vuln_id: str) -> Severity:
        """Map vulnerability ID to severity (simplified)."""
        # In production, would query CVE database for CVSS score
        if vuln_id.startswith("GHSA"):
            return Severity.HIGH  # GitHub advisories tend to be higher severity
        elif vuln_id.startswith("CVE"):
            return Severity.MEDIUM  # Default for CVEs
        return Severity.LOW
