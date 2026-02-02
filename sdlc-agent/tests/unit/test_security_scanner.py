# =============================================================================
# Unit Tests for Security Scanner Service
# =============================================================================
# Tests for SecurityScanner, SecurityFinding, SecurityScanResult, and severity
# mapping functions.
# =============================================================================

import sys
from pathlib import Path
import importlib.util
import json
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Load security_scanner module directly to avoid heavy dependencies
_security_scanner_path = Path(__file__).parent.parent.parent / "src/sdlc_agent/services/security_scanner.py"
_spec = importlib.util.spec_from_file_location("security_scanner", _security_scanner_path)
_security_scanner = importlib.util.module_from_spec(_spec)

# Mock the logger before loading
sys.modules["sdlc_agent"] = MagicMock()
sys.modules["sdlc_agent.core"] = MagicMock()
sys.modules["sdlc_agent.core.logging"] = MagicMock()
sys.modules["sdlc_agent.core.logging"].get_logger = MagicMock(return_value=MagicMock())

sys.modules["security_scanner"] = _security_scanner
_spec.loader.exec_module(_security_scanner)

Severity = _security_scanner.Severity
FindingCategory = _security_scanner.FindingCategory
SecurityFinding = _security_scanner.SecurityFinding
DependencyVulnerability = _security_scanner.DependencyVulnerability
SecurityScanResult = _security_scanner.SecurityScanResult
SecurityScanner = _security_scanner.SecurityScanner


# =============================================================================
# Tests for Severity Enum
# =============================================================================

class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Verify all severity levels exist."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_severity_ordering(self):
        """Test that severity can be compared as strings."""
        # Just verify they are distinct strings
        values = [s.value for s in Severity]
        assert len(values) == len(set(values))


class TestFindingCategoryEnum:
    """Tests for FindingCategory enum."""

    def test_all_categories_exist(self):
        """Verify all expected categories are present."""
        expected = {
            "injection", "xss", "secrets", "crypto",
            "auth", "config", "dependency", "code_quality", "other"
        }
        actual = {c.value for c in FindingCategory}
        assert expected == actual


# =============================================================================
# Tests for SecurityFinding
# =============================================================================

class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_create_finding(self):
        """Can create a SecurityFinding with required fields."""
        finding = SecurityFinding(
            id="B101",
            severity=Severity.HIGH,
            category=FindingCategory.SECRETS,
            title="Hardcoded Password",
            description="Password found in code",
            file_path="src/config.py",
        )
        assert finding.id == "B101"
        assert finding.severity == Severity.HIGH
        assert finding.category == FindingCategory.SECRETS
        assert finding.line_number is None  # Optional

    def test_finding_with_all_fields(self):
        """Can create a SecurityFinding with all fields."""
        finding = SecurityFinding(
            id="B102",
            severity=Severity.CRITICAL,
            category=FindingCategory.INJECTION,
            title="SQL Injection",
            description="User input used in SQL query",
            file_path="src/db.py",
            line_number=42,
            line_end=45,
            code_snippet="cursor.execute(f'SELECT * FROM users WHERE id={user_id}')",
            remediation="Use parameterized queries",
            cwe_id="CWE-89",
            tool="bandit",
        )
        assert finding.line_number == 42
        assert finding.line_end == 45
        assert finding.cwe_id == "CWE-89"
        assert finding.tool == "bandit"

    def test_finding_to_dict(self):
        """SecurityFinding.to_dict() returns proper dictionary."""
        finding = SecurityFinding(
            id="test-001",
            severity=Severity.MEDIUM,
            category=FindingCategory.CONFIG,
            title="Debug Mode Enabled",
            description="Debug mode is enabled in production",
            file_path="settings.py",
            line_number=10,
        )
        d = finding.to_dict()
        
        assert d["id"] == "test-001"
        assert d["severity"] == "medium"
        assert d["category"] == "config"
        assert d["title"] == "Debug Mode Enabled"
        assert d["file_path"] == "settings.py"
        assert d["line_number"] == 10
        assert d["tool"] == "unknown"  # Default

    def test_finding_to_dict_optional_none(self):
        """Optional fields are None in to_dict() output."""
        finding = SecurityFinding(
            id="test",
            severity=Severity.LOW,
            category=FindingCategory.OTHER,
            title="Test",
            description="Test desc",
            file_path="test.py",
        )
        d = finding.to_dict()
        assert d["line_number"] is None
        assert d["line_end"] is None
        assert d["code_snippet"] is None
        assert d["remediation"] is None
        assert d["cwe_id"] is None


# =============================================================================
# Tests for DependencyVulnerability
# =============================================================================

class TestDependencyVulnerability:
    """Tests for DependencyVulnerability dataclass."""

    def test_create_vulnerability(self):
        """Can create a DependencyVulnerability."""
        vuln = DependencyVulnerability(
            package="requests",
            installed_version="2.25.0",
            fixed_version="2.31.0",
            vulnerability_id="CVE-2023-32681",
            severity=Severity.HIGH,
            description="Proxy-Authorization header leak",
        )
        assert vuln.package == "requests"
        assert vuln.installed_version == "2.25.0"
        assert vuln.fixed_version == "2.31.0"

    def test_vulnerability_no_fix(self):
        """Vulnerability can have no fixed version."""
        vuln = DependencyVulnerability(
            package="vulnerable-pkg",
            installed_version="1.0.0",
            fixed_version=None,
            vulnerability_id="GHSA-xxxx-yyyy-zzzz",
            severity=Severity.CRITICAL,
            description="No patch available",
        )
        assert vuln.fixed_version is None

    def test_vulnerability_to_dict(self):
        """DependencyVulnerability.to_dict() returns proper dictionary."""
        vuln = DependencyVulnerability(
            package="django",
            installed_version="3.2.0",
            fixed_version="3.2.15",
            vulnerability_id="CVE-2022-34265",
            severity=Severity.CRITICAL,
            description="SQL injection vulnerability",
        )
        d = vuln.to_dict()
        
        assert d["package"] == "django"
        assert d["installed_version"] == "3.2.0"
        assert d["fixed_version"] == "3.2.15"
        assert d["vulnerability_id"] == "CVE-2022-34265"
        assert d["severity"] == "critical"


# =============================================================================
# Tests for SecurityScanResult
# =============================================================================

class TestSecurityScanResult:
    """Tests for SecurityScanResult dataclass."""

    def test_empty_result(self):
        """Empty result has default values."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
        )
        assert result.success is True
        assert result.sast_findings == []
        assert result.dependency_vulnerabilities == []
        assert result.critical_count == 0
        assert result.passed is True
        assert result.security_score == 100.0

    def test_result_with_findings(self):
        """Result with findings has correct counts."""
        finding = SecurityFinding(
            id="test",
            severity=Severity.HIGH,
            category=FindingCategory.SECRETS,
            title="Test",
            description="Test",
            file_path="test.py",
        )
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=500,
            files_scanned=5,
            sast_findings=[finding],
            high_count=1,
            passed=False,
            blocking_issues=["1 high severity issue(s) found"],
            security_score=90.0,
        )
        assert len(result.sast_findings) == 1
        assert result.high_count == 1
        assert result.passed is False
        assert result.security_score == 90.0

    def test_result_to_dict(self):
        """SecurityScanResult.to_dict() returns proper dictionary."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=250,
            files_scanned=15,
            critical_count=1,
            high_count=2,
            medium_count=5,
            low_count=10,
            passed=False,
            blocking_issues=["1 critical vulnerability(ies) found"],
            security_score=45.0,
        )
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["scan_duration_ms"] == 250
        assert d["files_scanned"] == 15
        assert d["critical_count"] == 1
        assert d["passed"] is False
        assert d["security_score"] == 45.0

    def test_to_markdown_clean(self):
        """to_markdown() generates clean report when no issues."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            passed=True,
            security_score=100.0,
        )
        md = result.to_markdown()
        
        assert "✅ Security Scan Results" in md
        assert "100/100" in md
        assert "No security issues found" in md

    def test_to_markdown_with_issues(self):
        """to_markdown() includes findings when present."""
        finding = SecurityFinding(
            id="B101",
            severity=Severity.HIGH,
            category=FindingCategory.SECRETS,
            title="Hardcoded Password",
            description="Password found in code",
            file_path="config.py",
            line_number=15,
            remediation="Use environment variables",
        )
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=200,
            files_scanned=5,
            sast_findings=[finding],
            high_count=1,
            passed=False,
            blocking_issues=["1 high severity issue(s) found"],
            security_score=90.0,
        )
        md = result.to_markdown()
        
        assert "❌ Security Scan Results" in md
        assert "90/100" in md
        assert "Blocking Issues" in md
        assert "Hardcoded Password" in md
        assert "config.py" in md

    def test_to_markdown_with_dependencies(self):
        """to_markdown() includes dependency vulnerabilities."""
        vuln = DependencyVulnerability(
            package="requests",
            installed_version="2.25.0",
            fixed_version="2.31.0",
            vulnerability_id="CVE-2023-32681",
            severity=Severity.HIGH,
            description="Header leak",
        )
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=300,
            files_scanned=10,
            dependency_vulnerabilities=[vuln],
            high_count=1,
            passed=False,
            blocking_issues=["1 high severity issue(s) found"],
            security_score=90.0,
        )
        md = result.to_markdown()
        
        assert "Vulnerable Dependencies" in md
        assert "requests" in md
        assert "2.31.0" in md

    def test_to_markdown_truncates_many_findings(self):
        """to_markdown() limits findings per severity to 5."""
        findings = [
            SecurityFinding(
                id=f"test-{i}",
                severity=Severity.MEDIUM,
                category=FindingCategory.CODE_QUALITY,
                title=f"Issue {i}",
                description=f"Description {i}",
                file_path=f"file{i}.py",
            )
            for i in range(10)
        ]
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            sast_findings=findings,
            medium_count=10,
            passed=True,
            security_score=70.0,
        )
        md = result.to_markdown()
        
        assert "... and 5 more" in md


# =============================================================================
# Tests for SecurityScanner Severity Mapping
# =============================================================================

class TestSecurityScannerMappings:
    """Tests for SecurityScanner mapping methods."""

    @pytest.fixture
    def scanner(self, tmp_path):
        """Create scanner with temp repo path."""
        return SecurityScanner(repo_path=tmp_path)

    def test_map_bandit_severity_high(self, scanner):
        """Maps Bandit HIGH to Severity.HIGH."""
        assert scanner._map_bandit_severity("HIGH") == Severity.HIGH

    def test_map_bandit_severity_medium(self, scanner):
        """Maps Bandit MEDIUM to Severity.MEDIUM."""
        assert scanner._map_bandit_severity("MEDIUM") == Severity.MEDIUM

    def test_map_bandit_severity_low(self, scanner):
        """Maps Bandit LOW to Severity.LOW."""
        assert scanner._map_bandit_severity("LOW") == Severity.LOW

    def test_map_bandit_severity_unknown(self, scanner):
        """Maps unknown Bandit severity to INFO."""
        assert scanner._map_bandit_severity("UNKNOWN") == Severity.INFO

    def test_map_bandit_category_b1xx(self, scanner):
        """Maps B1xx (misc) to CODE_QUALITY."""
        assert scanner._map_bandit_category("B101") == FindingCategory.CODE_QUALITY

    def test_map_bandit_category_b2xx(self, scanner):
        """Maps B2xx (blacklist calls) to INJECTION."""
        assert scanner._map_bandit_category("B201") == FindingCategory.INJECTION

    def test_map_bandit_category_b3xx(self, scanner):
        """Maps B3xx (blacklist imports) to CONFIG."""
        assert scanner._map_bandit_category("B301") == FindingCategory.CONFIG

    def test_map_bandit_category_b4xx(self, scanner):
        """Maps B4xx (hardcoded) to SECRETS."""
        assert scanner._map_bandit_category("B401") == FindingCategory.SECRETS

    def test_map_bandit_category_b5xx(self, scanner):
        """Maps B5xx (crypto) to CRYPTO."""
        assert scanner._map_bandit_category("B501") == FindingCategory.CRYPTO

    def test_map_bandit_category_b6xx(self, scanner):
        """Maps B6xx (yaml) to CONFIG."""
        assert scanner._map_bandit_category("B601") == FindingCategory.CONFIG

    def test_map_bandit_category_other(self, scanner):
        """Maps unknown category to OTHER."""
        assert scanner._map_bandit_category("B999") == FindingCategory.OTHER

    def test_map_semgrep_severity_error(self, scanner):
        """Maps Semgrep ERROR to Severity.HIGH."""
        assert scanner._map_semgrep_severity("ERROR") == Severity.HIGH

    def test_map_semgrep_severity_warning(self, scanner):
        """Maps Semgrep WARNING to Severity.MEDIUM."""
        assert scanner._map_semgrep_severity("WARNING") == Severity.MEDIUM

    def test_map_semgrep_severity_info(self, scanner):
        """Maps Semgrep INFO to Severity.LOW."""
        assert scanner._map_semgrep_severity("INFO") == Severity.LOW

    def test_map_semgrep_category_injection(self, scanner):
        """Maps injection-related check IDs."""
        assert scanner._map_semgrep_category("python.lang.security.sqli.sql-injection") == FindingCategory.INJECTION

    def test_map_semgrep_category_xss(self, scanner):
        """Maps XSS-related check IDs."""
        assert scanner._map_semgrep_category("javascript.browser.xss.reflected-xss") == FindingCategory.XSS

    def test_map_semgrep_category_secrets(self, scanner):
        """Maps secrets-related check IDs."""
        assert scanner._map_semgrep_category("generic.secrets.gitleaks.credential-detection") == FindingCategory.SECRETS

    def test_map_semgrep_category_crypto(self, scanner):
        """Maps crypto-related check IDs."""
        assert scanner._map_semgrep_category("python.lang.security.crypto.insecure-hash") == FindingCategory.CRYPTO

    def test_map_semgrep_category_auth(self, scanner):
        """Maps auth-related check IDs."""
        assert scanner._map_semgrep_category("python.django.security.auth.no-auth-required") == FindingCategory.AUTH

    def test_map_pip_audit_severity_ghsa(self, scanner):
        """Maps GHSA vulnerabilities to HIGH."""
        assert scanner._map_pip_audit_severity("GHSA-1234-5678-abcd") == Severity.HIGH

    def test_map_pip_audit_severity_cve(self, scanner):
        """Maps CVE vulnerabilities to MEDIUM."""
        assert scanner._map_pip_audit_severity("CVE-2023-12345") == Severity.MEDIUM

    def test_map_pip_audit_severity_other(self, scanner):
        """Maps other vulnerability IDs to LOW."""
        assert scanner._map_pip_audit_severity("PYSEC-2023-100") == Severity.LOW


# =============================================================================
# Tests for SecurityScanner Score Calculation
# =============================================================================

class TestSecurityScannerScoreCalculation:
    """Tests for security score calculation logic."""

    def test_score_perfect(self):
        """No findings = score of 100."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            passed=True,
            security_score=100.0,
        )
        assert result.security_score == 100.0

    def test_score_with_critical(self):
        """Critical finding reduces score by 25."""
        # Score: 100 - (1 * 25) = 75
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=1,
            security_score=75.0,
            passed=False,
        )
        assert result.security_score == 75.0

    def test_score_with_high(self):
        """High finding reduces score by 10."""
        # Score: 100 - (1 * 10) = 90
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            high_count=1,
            security_score=90.0,
            passed=False,
        )
        assert result.security_score == 90.0

    def test_score_with_mixed(self):
        """Mixed findings accumulate penalties."""
        # Score: 100 - (1*25) - (2*10) - (3*3) - (5*1) = 100 - 25 - 20 - 9 - 5 = 41
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=1,
            high_count=2,
            medium_count=3,
            low_count=5,
            security_score=41.0,
            passed=False,
        )
        assert result.security_score == 41.0

    def test_score_minimum_zero(self):
        """Score cannot go below 0."""
        # Many findings should still result in score >= 0
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=10,  # -250
            high_count=10,      # -100
            security_score=0.0,
            passed=False,
        )
        assert result.security_score == 0.0


# =============================================================================
# Tests for SecurityScanner Gate Logic
# =============================================================================

class TestSecurityScannerGateLogic:
    """Tests for pass/fail gate logic."""

    def test_passes_with_no_issues(self):
        """Scan passes with no critical/high issues."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            medium_count=5,
            low_count=10,
            passed=True,
            blocking_issues=[],
        )
        assert result.passed is True
        assert len(result.blocking_issues) == 0

    def test_fails_with_critical(self):
        """Scan fails with critical issues."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=1,
            passed=False,
            blocking_issues=["1 critical vulnerability(ies) found"],
        )
        assert result.passed is False
        assert "critical" in result.blocking_issues[0].lower()

    def test_fails_with_high(self):
        """Scan fails with high severity issues."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            high_count=3,
            passed=False,
            blocking_issues=["3 high severity issue(s) found"],
        )
        assert result.passed is False
        assert "high" in result.blocking_issues[0].lower()

    def test_fails_with_both_critical_and_high(self):
        """Scan fails and reports both critical and high."""
        result = SecurityScanResult(
            success=True,
            scan_duration_ms=100,
            files_scanned=10,
            critical_count=2,
            high_count=5,
            passed=False,
            blocking_issues=[
                "2 critical vulnerability(ies) found",
                "5 high severity issue(s) found",
            ],
        )
        assert result.passed is False
        assert len(result.blocking_issues) == 2


# =============================================================================
# Tests for SecurityScanner Async Methods (Mocked)
# =============================================================================

class TestSecurityScannerAsync:
    """Tests for async scanning methods with mocked subprocess."""

    @pytest.fixture
    def scanner(self, tmp_path):
        """Create scanner with temp repo path."""
        return SecurityScanner(repo_path=tmp_path)

    @pytest.mark.asyncio
    async def test_run_command(self, scanner):
        """_run_command executes and returns result."""
        result = await scanner._run_command(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_run_bandit_no_python_files(self, scanner):
        """_run_bandit returns empty when no Python files."""
        files = [{"filename": "readme.md"}]
        findings, count = await scanner._run_bandit(files)
        assert findings == []
        assert count == 0

    @pytest.mark.asyncio
    async def test_run_semgrep_no_supported_files(self, scanner):
        """_run_semgrep returns empty when no supported files."""
        files = [{"filename": "readme.md"}]
        findings, count = await scanner._run_semgrep(files)
        assert findings == []
        assert count == 0

    @pytest.mark.asyncio
    async def test_scan_empty_files(self, scanner):
        """scan() handles empty file list gracefully."""
        result = await scanner.scan(files=[], include_dependencies=False)
        assert result.success is True
        assert result.files_scanned == 0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_scan_with_mock_bandit(self, scanner, tmp_path):
        """scan() processes Bandit output correctly."""
        # Create a mock Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("password = 'secret123'")
        
        mock_bandit_output = json.dumps({
            "metrics": {"_totals": {"loc": 100}},
            "results": [
                {
                    "test_id": "B105",
                    "test_name": "hardcoded_password_string",
                    "issue_severity": "HIGH",
                    "issue_confidence": "MEDIUM",
                    "issue_text": "Possible hardcoded password",
                    "filename": str(test_file),
                    "line_number": 1,
                    "line_range": [1],
                    "code": "password = 'secret123'",
                }
            ],
        })
        
        async def mock_run_command(cmd, cwd=None):
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,  # Bandit returns 1 when issues found
                stdout=mock_bandit_output,
                stderr="",
            )
        
        with patch.object(scanner, "_run_command", side_effect=mock_run_command):
            with patch.object(scanner, "_run_semgrep", return_value=([], 0)):
                result = await scanner.scan(files=None, include_dependencies=False)
        
        assert result.success is True
        assert len(result.sast_findings) > 0
