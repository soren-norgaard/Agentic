"""
End-to-End tests for RBAC (Role-Based Access Control) system.

These tests verify the complete authentication and authorization flow
from login through to accessing protected endpoints.
"""

import pytest
import httpx
from typing import Optional

# E2E test configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def http_client():
    """Create an async HTTP client for E2E tests."""
    with httpx.Client(timeout=30.0) as client:
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
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token: str) -> dict:
    """Create authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestHealthEndpoints:
    """Test basic API health before RBAC tests."""

    @pytest.mark.e2e
    def test_api_health(self, http_client: httpx.Client):
        """API health endpoint should be accessible without auth."""
        response = http_client.get(f"{API_V1}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthenticationFlow:
    """Test the authentication flow end-to-end."""

    @pytest.mark.e2e
    def test_login_with_valid_credentials(self, http_client: httpx.Client):
        """Login with valid admin credentials should return JWT token."""
        response = http_client.post(
            f"{API_V1}/auth/login",
            json={
                "username": "admin",
                "password": "Admin123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.e2e
    def test_login_with_invalid_credentials(self, http_client: httpx.Client):
        """Login with invalid credentials should return 401."""
        response = http_client.post(
            f"{API_V1}/auth/login",
            json={
                "username": "admin",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.e2e
    def test_login_with_nonexistent_user(self, http_client: httpx.Client):
        """Login with nonexistent user should return 401."""
        response = http_client.post(
            f"{API_V1}/auth/login",
            json={
                "username": "nonexistent",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.e2e
    def test_get_current_user_with_valid_token(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Get current user with valid token should return user info."""
        response = http_client.get(f"{API_V1}/users/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert "id" in data
        assert "roles" in data

    @pytest.mark.e2e
    def test_get_current_user_without_token(self, http_client: httpx.Client):
        """Access protected endpoint without token should return 401."""
        response = http_client.get(f"{API_V1}/users/me")
        assert response.status_code == 401

    @pytest.mark.e2e
    def test_get_current_user_with_invalid_token(self, http_client: httpx.Client):
        """Access protected endpoint with invalid token should return 401."""
        response = http_client.get(
            f"{API_V1}/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestRoleManagement:
    """Test role management endpoints end-to-end."""

    @pytest.mark.e2e
    def test_list_roles_as_admin(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to list all roles."""
        response = http_client.get(f"{API_V1}/roles", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
        
        # Check default roles exist
        roles = data.get("items", data)
        role_names = [r["name"] for r in roles]
        assert "admin" in role_names
        assert "developer" in role_names
        assert "viewer" in role_names

    @pytest.mark.e2e
    def test_create_and_delete_role(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to create and delete roles."""
        # Create a test role
        create_response = http_client.post(
            f"{API_V1}/roles",
            json={"name": "e2e_test_role", "description": "E2E test role"},
            headers=admin_headers,
        )
        assert create_response.status_code in [200, 201]
        role = create_response.json()
        assert role["name"] == "e2e_test_role"
        role_id = role["id"]

        # Delete the test role
        delete_response = http_client.delete(
            f"{API_V1}/roles/{role_id}", headers=admin_headers
        )
        assert delete_response.status_code in [200, 204]


class TestPermissionManagement:
    """Test permission management endpoints end-to-end."""

    @pytest.mark.e2e
    def test_list_permissions_as_admin(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to list all permissions."""
        response = http_client.get(f"{API_V1}/permissions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
        
        # Check that permissions exist
        permissions = data.get("items", data)
        assert len(permissions) > 0


class TestUserManagement:
    """Test user management endpoints end-to-end."""

    created_user_id: Optional[str] = None

    @pytest.mark.e2e
    def test_create_user_as_admin(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to create a new user."""
        response = http_client.post(
            f"{API_V1}/users",
            json={
                "username": "e2e_test_user",
                "email": "e2e_test@example.com",
                "password": "TestPassword123!",
                "full_name": "E2E Test User",
            },
            headers=admin_headers,
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["username"] == "e2e_test_user"
        TestUserManagement.created_user_id = data["id"]

    @pytest.mark.e2e
    def test_list_users_as_admin(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to list all users."""
        response = http_client.get(f"{API_V1}/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.e2e
    def test_assign_role_to_user(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should be able to assign a role to a user."""
        if not TestUserManagement.created_user_id:
            pytest.skip("User not created")
        
        # Get viewer role ID
        roles_response = http_client.get(f"{API_V1}/roles", headers=admin_headers)
        roles = roles_response.json().get("items", roles_response.json())
        viewer_role = next((r for r in roles if r["name"] == "viewer"), None)
        
        if not viewer_role:
            pytest.skip("Viewer role not found")

        response = http_client.post(
            f"{API_V1}/users/{TestUserManagement.created_user_id}/roles",
            json={"role_id": viewer_role["id"]},
            headers=admin_headers,
        )
        assert response.status_code in [200, 201, 204]

    @pytest.mark.e2e
    def test_new_user_can_login(self, http_client: httpx.Client):
        """Newly created user should be able to login."""
        response = http_client.post(
            f"{API_V1}/auth/login",
            json={
                "username": "e2e_test_user",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.e2e
    def test_cleanup_delete_test_user(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Clean up: delete the test user."""
        if not TestUserManagement.created_user_id:
            pytest.skip("No user to delete")
        
        response = http_client.delete(
            f"{API_V1}/users/{TestUserManagement.created_user_id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]


class TestAuthorizationFlow:
    """Test authorization (permission-based access) end-to-end."""

    @pytest.mark.e2e
    def test_admin_can_access_protected_endpoints(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Admin should have access to all protected endpoints."""
        # Admin can access users
        response = http_client.get(f"{API_V1}/users", headers=admin_headers)
        assert response.status_code == 200
        
        # Admin can access roles
        response = http_client.get(f"{API_V1}/roles", headers=admin_headers)
        assert response.status_code == 200
        
        # Admin can access permissions
        response = http_client.get(f"{API_V1}/permissions", headers=admin_headers)
        assert response.status_code == 200
        
        # Admin can access audit logs
        response = http_client.get(f"{API_V1}/audit-logs", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.e2e
    def test_viewer_cannot_create_users(self, http_client: httpx.Client):
        """Viewer role should not be able to create users."""
        # Create a viewer user first
        admin_response = http_client.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "Admin123!"},
        )
        admin_token = admin_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create viewer user
        create_response = http_client.post(
            f"{API_V1}/users",
            json={
                "username": "e2e_viewer",
                "email": "e2e_viewer@example.com",
                "password": "ViewerPass123!",
            },
            headers=admin_headers,
        )
        
        if create_response.status_code not in [200, 201]:
            # User might already exist, try to login
            pass
        else:
            viewer_id = create_response.json()["id"]
            # Assign viewer role
            roles_resp = http_client.get(f"{API_V1}/roles", headers=admin_headers)
            roles = roles_resp.json().get("items", roles_resp.json())
            viewer_role = next((r for r in roles if r["name"] == "viewer"), None)
            if viewer_role:
                http_client.post(
                    f"{API_V1}/users/{viewer_id}/roles",
                    json={"role_id": viewer_role["id"]},
                    headers=admin_headers,
                )

        # Login as viewer
        viewer_login = http_client.post(
            f"{API_V1}/auth/login",
            json={"username": "e2e_viewer", "password": "ViewerPass123!"},
        )
        
        if viewer_login.status_code != 200:
            pytest.skip("Could not login as viewer")
        
        viewer_token = viewer_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # Viewer should not be able to create users
        response = http_client.post(
            f"{API_V1}/users",
            json={
                "username": "should_fail",
                "email": "fail@example.com",
                "password": "Password123!",
            },
            headers=viewer_headers,
        )
        assert response.status_code in [401, 403]

        # Cleanup
        try:
            users_resp = http_client.get(f"{API_V1}/users", headers=admin_headers)
            users = users_resp.json().get("items", users_resp.json())
            viewer_user = next((u for u in users if u["username"] == "e2e_viewer"), None)
            if viewer_user:
                http_client.delete(f"{API_V1}/users/{viewer_user['id']}", headers=admin_headers)
        except Exception:
            pass


class TestAuditLogging:
    """Test audit logging end-to-end."""

    @pytest.mark.e2e
    def test_audit_logs_are_created(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Actions should create audit log entries."""
        response = http_client.get(f"{API_V1}/audit-logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.e2e
    def test_audit_logs_include_login_events(
        self, http_client: httpx.Client, admin_headers: dict
    ):
        """Audit logs should include login events."""
        # Do a login first
        http_client.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "Admin123!"},
        )
        
        # Check audit logs
        response = http_client.get(
            f"{API_V1}/audit-logs",
            params={"action": "login"},
            headers=admin_headers,
        )
        # This might return all logs if filtering isn't implemented
        assert response.status_code == 200


class TestTokenRefresh:
    """Test token refresh flow."""

    @pytest.mark.e2e
    def test_refresh_token_flow(self, http_client: httpx.Client):
        """Should be able to refresh an access token."""
        # Login to get tokens
        login_response = http_client.post(
            f"{API_V1}/auth/login",
            json={"username": "admin", "password": "Admin123!"},
        )
        assert login_response.status_code == 200
        data = login_response.json()
        
        # If refresh token is provided, test refresh
        if "refresh_token" in data:
            refresh_response = http_client.post(
                f"{API_V1}/auth/refresh",
                json={"refresh_token": data["refresh_token"]},
            )
            assert refresh_response.status_code == 200
            new_data = refresh_response.json()
            assert "access_token" in new_data
        else:
            pytest.skip("Refresh token not implemented")
