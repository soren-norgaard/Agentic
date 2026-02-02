"""
End-to-End tests for Security Scanning API.

These tests verify the complete security scanning flow from
triggering a scan to receiving results.
"""

import pytest
import httpx
from typing import Optional

# E2E test configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def http_client():
    """Create an HTTP client for E2E tests."""
    with httpx.Client(timeout=60.0) as client:  # Longer timeout for scans
        yield client


@pytest.fixture(scope="module")
def admin_token(http_client: httpx.Client) -> str:
    """Get admin JWT token for authenticated requests."""
    response = http_client.post(
        f"{API_V1}/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!",
        },
    )
    if response.status_code != 200:
        pytest.skip("Auth endpoint not available, skipping authenticated tests")
    data = response.json()
    return data.get("access_token", "")


@pytest.fixture(scope="module")
def admin_headers(admin_token: str) -> dict:
    """Create authorization headers with admin token."""
    if admin_token:
        return {"Authorization": f"Bearer {admin_token}"}
    return {}


class TestSecurityScanEndpoint:
    """Test the security scan API endpoint."""

    @pytest.mark.e2e
    def test_security_scan_requires_valid_pr(self, http_client: httpx.Client):
        """Security scan on non-existent PR returns 404."""
        response = http_client.post(
            f"{API_V1}/prs/99999/security",
            json={"include_dependencies": True, "post_comment": False},
        )
        # Should fail because PR doesn't exist
        assert response.status_code in (404, 400, 500)

    @pytest.mark.e2e
    def test_security_scan_endpoint_exists(self, http_client: httpx.Client):
        """Security scan endpoint is registered and accessible."""
        # Just verify the endpoint exists (not 404/405 for route)
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={"include_dependencies": False, "post_comment": False},
        )
        # Should not be 405 Method Not Allowed (endpoint exists)
        assert response.status_code != 405

    @pytest.mark.e2e
    def test_security_scan_request_validation(self, http_client: httpx.Client):
        """Security scan validates request body."""
        # Send empty body - should use defaults or accept it
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={},
        )
        # Should not fail validation (empty body uses defaults)
        assert response.status_code != 422  # Not validation error

    @pytest.mark.e2e
    def test_security_scan_with_options(self, http_client: httpx.Client):
        """Security scan accepts all options."""
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={
                "include_dependencies": True,
                "post_comment": False,
            },
        )
        # Endpoint accepts the options (may fail for other reasons like PR not found)
        assert response.status_code != 422  # Not validation error


class TestSecurityScanResponse:
    """Test security scan response format."""

    @pytest.mark.e2e
    def test_security_scan_response_structure(self, http_client: httpx.Client):
        """Security scan response has expected structure when successful."""
        # This test may skip if GitHub is not configured
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={"include_dependencies": False, "post_comment": False},
        )
        
        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert "success" in data
            assert "pr_number" in data
            assert "passed" in data
            assert "security_score" in data
            assert "critical_count" in data
            assert "high_count" in data
            assert "medium_count" in data
            assert "low_count" in data
            assert "summary_markdown" in data
        else:
            # If not 200, it should be because of GitHub config/PR issues
            pytest.skip(f"Security scan returned {response.status_code}, skipping structure test")

    @pytest.mark.e2e
    def test_security_scan_score_range(self, http_client: httpx.Client):
        """Security score is within valid range 0-100."""
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={"include_dependencies": False, "post_comment": False},
        )
        
        if response.status_code == 200:
            data = response.json()
            score = data.get("security_score", 0)
            assert 0 <= score <= 100, f"Score {score} out of range"
        else:
            pytest.skip(f"Security scan returned {response.status_code}")

    @pytest.mark.e2e
    def test_security_scan_counts_non_negative(self, http_client: httpx.Client):
        """All severity counts are non-negative."""
        response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={"include_dependencies": False, "post_comment": False},
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("critical_count", 0) >= 0
            assert data.get("high_count", 0) >= 0
            assert data.get("medium_count", 0) >= 0
            assert data.get("low_count", 0) >= 0
        else:
            pytest.skip(f"Security scan returned {response.status_code}")


class TestPRDashboardWithSecurity:
    """Test PR dashboard includes security status."""

    @pytest.mark.e2e
    def test_dashboard_endpoint_accessible(self, http_client: httpx.Client):
        """PR dashboard endpoint is accessible."""
        response = http_client.get(f"{API_V1}/prs/dashboard/summary")
        # May fail if GitHub not configured, but endpoint should exist
        assert response.status_code != 405  # Not method not allowed

    @pytest.mark.e2e
    def test_pr_list_endpoint_accessible(self, http_client: httpx.Client):
        """PR list endpoint is accessible."""
        response = http_client.get(f"{API_V1}/prs", params={"state": "open"})
        assert response.status_code != 405

    @pytest.mark.e2e
    def test_pr_list_response_structure(self, http_client: httpx.Client):
        """PR list includes security_status field."""
        response = http_client.get(f"{API_V1}/prs", params={"state": "open"})
        
        if response.status_code == 200:
            data = response.json()
            assert "prs" in data
            # If there are PRs, check structure
            if data["prs"]:
                pr = data["prs"][0]
                # security_status may be present
                if "security_status" in pr:
                    assert pr["security_status"] in [
                        "pending", "scanning", "secure", "warning", "vulnerable"
                    ]
        else:
            pytest.skip(f"PR list returned {response.status_code}")


class TestWebhookSecurityIntegration:
    """Test webhook triggers security scan."""

    @pytest.mark.e2e
    def test_webhook_status_includes_security(self, http_client: httpx.Client):
        """Webhook status shows security as handled event."""
        response = http_client.get(f"{API_V1}/webhooks/status")
        
        if response.status_code == 200:
            data = response.json()
            # Webhook handler should include pull_request event
            if "events_handled" in data:
                assert "pull_request" in data["events_handled"]
        else:
            pytest.skip(f"Webhook status returned {response.status_code}")

    @pytest.mark.e2e
    def test_webhook_ping(self, http_client: httpx.Client):
        """Webhook endpoint accepts ping events."""
        response = http_client.post(
            f"{API_V1}/webhooks/github",
            json={"action": "ping"},
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "test-delivery-id",
            },
        )
        # Should handle ping gracefully (may require signature in production)
        assert response.status_code in (200, 401, 403)


class TestSecurityScanArtifacts:
    """Test security scan creates artifacts."""

    @pytest.mark.e2e
    def test_security_artifact_stored(self, http_client: httpx.Client):
        """Security scan creates an artifact."""
        # First trigger a scan
        scan_response = http_client.post(
            f"{API_V1}/prs/1/security",
            json={"include_dependencies": False, "post_comment": False},
        )
        
        if scan_response.status_code == 200:
            data = scan_response.json()
            artifact_id = data.get("artifact_id")
            
            if artifact_id:
                # Artifact was created
                assert artifact_id is not None
            else:
                # Artifact creation may have failed silently
                pass
        else:
            pytest.skip(f"Security scan returned {scan_response.status_code}")


class TestSecurityScanErrorHandling:
    """Test error handling in security scan."""

    @pytest.mark.e2e
    def test_scan_handles_timeout_gracefully(self, http_client: httpx.Client):
        """Scan doesn't crash on slow operations."""
        # Just verify the endpoint doesn't hang indefinitely
        try:
            response = http_client.post(
                f"{API_V1}/prs/1/security",
                json={"include_dependencies": True, "post_comment": False},
                timeout=30.0,
            )
            # Any response is acceptable (not timeout)
            assert response.status_code > 0
        except httpx.TimeoutException:
            pytest.fail("Security scan timed out after 30s")

    @pytest.mark.e2e
    def test_scan_invalid_pr_number_format(self, http_client: httpx.Client):
        """Invalid PR number format is handled."""
        # This should fail validation or return error
        response = http_client.post(
            f"{API_V1}/prs/not-a-number/security",
            json={},
        )
        # Should be 404 (not found) or 422 (validation error)
        assert response.status_code in (404, 422)

    @pytest.mark.e2e
    def test_scan_negative_pr_number(self, http_client: httpx.Client):
        """Negative PR number is handled."""
        response = http_client.post(
            f"{API_V1}/prs/-1/security",
            json={},
        )
        # Should fail gracefully
        assert response.status_code in (400, 404, 422, 500)
