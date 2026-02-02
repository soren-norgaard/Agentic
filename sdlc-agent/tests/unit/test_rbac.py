# =============================================================================
# SDLC Agent - RBAC Unit Tests
# =============================================================================
# Comprehensive tests for Role-Based Access Control system.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from sdlc_agent.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    check_permission,
    create_access_token,
    create_refresh_token,
    hash_password,
    require_all_permissions,
    require_any_permission,
    require_permission,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from sdlc_agent.core.exceptions import AuthenticationError, AuthorizationError


# =============================================================================
# Password Hashing Tests
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_hash(self) -> None:
        """Test that hash_password returns a bcrypt hash."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_hash_password_unique_hashes(self) -> None:
        """Test that same password produces different hashes (due to salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test that correct password verifies successfully."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test that incorrect password fails verification."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self) -> None:
        """Test that empty password fails verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False

    def test_hash_password_unicode(self) -> None:
        """Test that unicode passwords work correctly."""
        password = "Sécure密码123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


# =============================================================================
# JWT Token Tests
# =============================================================================


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    @pytest.fixture
    def user_data(self) -> dict:
        """Sample user data for token creation."""
        return {
            "user_id": uuid.uuid4(),
            "email": "test@example.com",
            "username": "testuser",
            "roles": ["developer", "viewer"],
            "permissions": ["projects:read:any", "tasks:read:any"],
        }

    def test_create_access_token(self, user_data: dict) -> None:
        """Test access token creation."""
        token = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
        )

        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are typically longer

    def test_create_refresh_token(self, user_data: dict) -> None:
        """Test refresh token creation."""
        token = create_refresh_token(user_id=user_data["user_id"])

        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_access_token_valid(self, user_data: dict) -> None:
        """Test verifying a valid access token."""
        token = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
        )

        token_data = verify_access_token(token)

        assert token_data.sub == str(user_data["user_id"])
        assert token_data.email == user_data["email"]
        assert token_data.username == user_data["username"]
        assert token_data.roles == user_data["roles"]
        assert token_data.permissions == user_data["permissions"]

    def test_verify_access_token_invalid(self) -> None:
        """Test that invalid token raises AuthenticationError."""
        with pytest.raises(AuthenticationError):
            verify_access_token("invalid.token.here")

    def test_verify_access_token_wrong_type(self, user_data: dict) -> None:
        """Test that refresh token fails access token verification."""
        refresh_token = create_refresh_token(user_id=user_data["user_id"])

        with pytest.raises(AuthenticationError, match="Invalid token type"):
            verify_access_token(refresh_token)

    def test_verify_refresh_token_valid(self, user_data: dict) -> None:
        """Test verifying a valid refresh token."""
        token = create_refresh_token(user_id=user_data["user_id"])

        payload = verify_refresh_token(token)

        assert payload["sub"] == str(user_data["user_id"])
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_wrong_type(self, user_data: dict) -> None:
        """Test that access token fails refresh token verification."""
        access_token = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
        )

        with pytest.raises(AuthenticationError, match="Invalid token type"):
            verify_refresh_token(access_token)

    def test_access_token_custom_expiration(self, user_data: dict) -> None:
        """Test access token with custom expiration."""
        custom_delta = timedelta(minutes=5)
        token = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
            expires_delta=custom_delta,
        )

        token_data = verify_access_token(token)
        now = datetime.now(UTC)

        # Token should expire within 5-6 minutes (allowing for test execution time)
        time_until_expiry = token_data.exp - now
        assert timedelta(minutes=4) < time_until_expiry < timedelta(minutes=6)

    def test_token_contains_unique_jti(self, user_data: dict) -> None:
        """Test that each token has a unique JTI."""
        token1 = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
        )
        token2 = create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
        )

        data1 = verify_access_token(token1)
        data2 = verify_access_token(token2)

        assert data1.jti != data2.jti


# =============================================================================
# Permission Checking Tests
# =============================================================================


class TestPermissionChecking:
    """Tests for permission checking functions."""

    def test_check_permission_direct_match(self) -> None:
        """Test direct permission match."""
        user_permissions = {"projects:read:any", "tasks:read:own"}

        assert check_permission(user_permissions, "projects:read:any") is True
        assert check_permission(user_permissions, "tasks:read:own") is True

    def test_check_permission_no_match(self) -> None:
        """Test permission not in set."""
        user_permissions = {"projects:read:any"}

        assert check_permission(user_permissions, "projects:delete:any") is False
        assert check_permission(user_permissions, "users:read:any") is False

    def test_check_permission_superuser_wildcard(self) -> None:
        """Test superuser wildcard permission."""
        user_permissions = {"*"}

        assert check_permission(user_permissions, "projects:read:any") is True
        assert check_permission(user_permissions, "users:delete:any") is True
        assert check_permission(user_permissions, "anything:whatever:scope") is True

    def test_check_permission_wildcard_action(self) -> None:
        """Test wildcard action permission."""
        user_permissions = {"projects:*:any"}

        assert check_permission(user_permissions, "projects:read:any") is True
        assert check_permission(user_permissions, "projects:write:any") is True
        assert check_permission(user_permissions, "projects:delete:any") is True
        # Should not match own scope with wildcard any
        assert check_permission(user_permissions, "tasks:read:any") is False

    def test_check_permission_any_includes_own(self) -> None:
        """Test that 'any' scope includes 'own' scope."""
        user_permissions = {"projects:read:any"}

        assert check_permission(user_permissions, "projects:read:any") is True
        assert check_permission(user_permissions, "projects:read:own") is True

    def test_check_permission_own_does_not_include_any(self) -> None:
        """Test that 'own' scope does not include 'any' scope."""
        user_permissions = {"projects:read:own"}

        assert check_permission(user_permissions, "projects:read:own") is True
        assert check_permission(user_permissions, "projects:read:any") is False

    def test_check_permission_invalid_format(self) -> None:
        """Test invalid permission format returns False."""
        user_permissions = {"projects:read:any"}

        assert check_permission(user_permissions, "invalid") is False
        assert check_permission(user_permissions, "only:two") is False
        assert check_permission(user_permissions, "too:many:parts:here") is False

    def test_check_permission_empty_set(self) -> None:
        """Test empty permission set."""
        user_permissions: set[str] = set()

        assert check_permission(user_permissions, "projects:read:any") is False

    def test_check_permission_wildcard_action_with_own(self) -> None:
        """Test wildcard action with 'any' scope checking 'own'."""
        user_permissions = {"projects:*:any"}

        # Wildcard any should include own
        assert check_permission(user_permissions, "projects:read:own") is True
        assert check_permission(user_permissions, "projects:write:own") is True


class TestRequirePermission:
    """Tests for require_permission function."""

    def test_require_permission_success(self) -> None:
        """Test require_permission passes with correct permission."""
        user_permissions = {"projects:read:any"}

        # Should not raise
        require_permission(user_permissions, "projects:read:any")

    def test_require_permission_failure(self) -> None:
        """Test require_permission raises with missing permission."""
        user_permissions = {"projects:read:any"}

        with pytest.raises(AuthorizationError, match="Permission denied"):
            require_permission(user_permissions, "projects:delete:any")


class TestRequireAnyPermission:
    """Tests for require_any_permission function."""

    def test_require_any_permission_first_match(self) -> None:
        """Test require_any_permission passes with first permission."""
        user_permissions = {"projects:read:any"}

        # Should not raise
        require_any_permission(
            user_permissions,
            ["projects:read:any", "tasks:read:any"],
        )

    def test_require_any_permission_second_match(self) -> None:
        """Test require_any_permission passes with second permission."""
        user_permissions = {"tasks:read:any"}

        # Should not raise
        require_any_permission(
            user_permissions,
            ["projects:read:any", "tasks:read:any"],
        )

    def test_require_any_permission_no_match(self) -> None:
        """Test require_any_permission raises with no matching permission."""
        user_permissions = {"users:read:any"}

        with pytest.raises(AuthorizationError, match="requires one of"):
            require_any_permission(
                user_permissions,
                ["projects:read:any", "tasks:read:any"],
            )


class TestRequireAllPermissions:
    """Tests for require_all_permissions function."""

    def test_require_all_permissions_success(self) -> None:
        """Test require_all_permissions passes with all permissions."""
        user_permissions = {"projects:read:any", "tasks:read:any"}

        # Should not raise
        require_all_permissions(
            user_permissions,
            ["projects:read:any", "tasks:read:any"],
        )

    def test_require_all_permissions_missing_one(self) -> None:
        """Test require_all_permissions raises with one missing permission."""
        user_permissions = {"projects:read:any"}

        with pytest.raises(AuthorizationError, match="Permission denied"):
            require_all_permissions(
                user_permissions,
                ["projects:read:any", "tasks:read:any"],
            )

    def test_require_all_permissions_missing_all(self) -> None:
        """Test require_all_permissions raises with all missing permissions."""
        user_permissions = {"users:read:any"}

        with pytest.raises(AuthorizationError, match="Permission denied"):
            require_all_permissions(
                user_permissions,
                ["projects:read:any", "tasks:read:any"],
            )


# =============================================================================
# RBAC Model Tests
# =============================================================================


class TestRBACModels:
    """Tests for RBAC database models."""

    def test_user_status_enum_values(self) -> None:
        """Test UserStatus enum has expected values."""
        from sdlc_agent.db.rbac_models import UserStatus

        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING_VERIFICATION.value == "pending_verification"

    def test_role_type_enum_values(self) -> None:
        """Test RoleType enum has expected values."""
        from sdlc_agent.db.rbac_models import RoleType

        assert RoleType.SYSTEM.value == "system"
        assert RoleType.CUSTOM.value == "custom"

    def test_audit_action_enum_has_auth_actions(self) -> None:
        """Test AuditAction enum has authentication actions."""
        from sdlc_agent.db.rbac_models import AuditAction

        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.LOGIN_FAILED.value == "login_failed"
        assert AuditAction.PASSWORD_CHANGED.value == "password_changed"

    def test_audit_action_enum_has_user_actions(self) -> None:
        """Test AuditAction enum has user management actions."""
        from sdlc_agent.db.rbac_models import AuditAction

        assert AuditAction.USER_CREATED.value == "user_created"
        assert AuditAction.USER_UPDATED.value == "user_updated"
        assert AuditAction.USER_DELETED.value == "user_deleted"

    def test_audit_action_enum_has_role_actions(self) -> None:
        """Test AuditAction enum has role management actions."""
        from sdlc_agent.db.rbac_models import AuditAction

        assert AuditAction.ROLE_CREATED.value == "role_created"
        assert AuditAction.ROLE_ASSIGNED.value == "role_assigned"
        assert AuditAction.ROLE_REVOKED.value == "role_revoked"

    def test_audit_action_enum_has_permission_actions(self) -> None:
        """Test AuditAction enum has permission management actions."""
        from sdlc_agent.db.rbac_models import AuditAction

        assert AuditAction.PERMISSION_GRANTED.value == "permission_granted"
        assert AuditAction.PERMISSION_REVOKED.value == "permission_revoked"

    def test_audit_action_enum_has_access_actions(self) -> None:
        """Test AuditAction enum has access control actions."""
        from sdlc_agent.db.rbac_models import AuditAction

        assert AuditAction.ACCESS_DENIED.value == "access_denied"
        assert AuditAction.ACCESS_GRANTED.value == "access_granted"


# =============================================================================
# RBAC Schema Tests
# =============================================================================


class TestRBACSchemas:
    """Tests for RBAC Pydantic schemas."""

    def test_user_create_validation(self) -> None:
        """Test UserCreate schema validation."""
        from sdlc_agent.api.schemas.rbac import UserCreate

        # Valid user
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password="SecurePass123!",
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_user_create_password_validation_uppercase(self) -> None:
        """Test UserCreate requires uppercase in password."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import UserCreate

        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                password="lowercase123!",
            )

    def test_user_create_password_validation_lowercase(self) -> None:
        """Test UserCreate requires lowercase in password."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import UserCreate

        with pytest.raises(ValidationError, match="lowercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                password="UPPERCASE123!",
            )

    def test_user_create_password_validation_digit(self) -> None:
        """Test UserCreate requires digit in password."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import UserCreate

        with pytest.raises(ValidationError, match="digit"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                password="NoDigitsHere!",
            )

    def test_user_create_username_pattern(self) -> None:
        """Test UserCreate username pattern validation."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import UserCreate

        # Valid usernames
        UserCreate(
            email="test@example.com",
            username="valid_user-name123",
            full_name="Test User",
            password="SecurePass123!",
        )

        # Invalid username with special chars
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="invalid@user",
                full_name="Test User",
                password="SecurePass123!",
            )

    def test_permission_create_code_pattern(self) -> None:
        """Test PermissionCreate code pattern validation."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import PermissionCreate

        # Valid code
        perm = PermissionCreate(
            code="projects:read:any",
            name="Read Projects",
            resource="projects",
            action="read",
            scope="any",
        )
        assert perm.code == "projects:read:any"

        # Invalid code format
        with pytest.raises(ValidationError):
            PermissionCreate(
                code="invalid-format",
                name="Invalid",
                resource="test",
                action="test",
                scope="test",
            )

    def test_login_request_schema(self) -> None:
        """Test LoginRequest schema."""
        from sdlc_agent.api.schemas.rbac import LoginRequest

        login = LoginRequest(username="testuser", password="password123")
        assert login.username == "testuser"
        assert login.password == "password123"

    def test_token_response_schema(self) -> None:
        """Test TokenResponse schema."""
        from sdlc_agent.api.schemas.rbac import TokenResponse

        response = TokenResponse(
            access_token="access.token.here",
            refresh_token="refresh.token.here",
            token_type="bearer",
            expires_in=1800,
        )
        assert response.token_type == "bearer"
        assert response.expires_in == 1800

    def test_role_create_priority_bounds(self) -> None:
        """Test RoleCreate priority validation bounds."""
        from pydantic import ValidationError

        from sdlc_agent.api.schemas.rbac import RoleCreate

        # Valid priority
        role = RoleCreate(name="test", priority=50)
        assert role.priority == 50

        # Too high
        with pytest.raises(ValidationError):
            RoleCreate(name="test", priority=101)

        # Negative
        with pytest.raises(ValidationError):
            RoleCreate(name="test", priority=-1)


# =============================================================================
# RBAC Seed Data Tests
# =============================================================================


class TestRBACSeedData:
    """Tests for RBAC seed data definitions."""

    def test_default_permissions_defined(self) -> None:
        """Test that default permissions are properly defined."""
        from sdlc_agent.db.rbac_seed import DEFAULT_PERMISSIONS

        assert len(DEFAULT_PERMISSIONS) > 0

        # Check structure
        for perm in DEFAULT_PERMISSIONS:
            assert "code" in perm
            assert "name" in perm
            assert "resource" in perm
            assert "action" in perm
            assert "scope" in perm

    def test_default_permissions_have_project_crud(self) -> None:
        """Test that project CRUD permissions exist."""
        from sdlc_agent.db.rbac_seed import DEFAULT_PERMISSIONS

        codes = {p["code"] for p in DEFAULT_PERMISSIONS}

        assert "projects:create:any" in codes
        assert "projects:read:any" in codes
        assert "projects:update:any" in codes
        assert "projects:delete:any" in codes

    def test_default_permissions_have_user_crud(self) -> None:
        """Test that user CRUD permissions exist."""
        from sdlc_agent.db.rbac_seed import DEFAULT_PERMISSIONS

        codes = {p["code"] for p in DEFAULT_PERMISSIONS}

        assert "users:create:any" in codes
        assert "users:read:any" in codes
        assert "users:update:any" in codes
        assert "users:delete:any" in codes

    def test_default_permissions_have_audit_read(self) -> None:
        """Test that audit read permission exists."""
        from sdlc_agent.db.rbac_seed import DEFAULT_PERMISSIONS

        codes = {p["code"] for p in DEFAULT_PERMISSIONS}

        assert "audit:read:any" in codes

    def test_default_roles_defined(self) -> None:
        """Test that default roles are properly defined."""
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        role_names = {r["name"] for r in DEFAULT_ROLES}

        assert "admin" in role_names
        assert "developer" in role_names
        assert "viewer" in role_names
        assert "guest" in role_names

    def test_admin_role_is_system_type(self) -> None:
        """Test that admin role is a system role."""
        from sdlc_agent.db.rbac_models import RoleType
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        admin_role = next(r for r in DEFAULT_ROLES if r["name"] == "admin")

        assert admin_role["role_type"] == RoleType.SYSTEM
        assert admin_role["priority"] == 100

    def test_admin_role_has_all_permissions(self) -> None:
        """Test that admin role has wildcard permission."""
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        admin_role = next(r for r in DEFAULT_ROLES if r["name"] == "admin")

        assert admin_role["permissions"] == ["*"]

    def test_developer_role_has_project_access(self) -> None:
        """Test that developer role has project permissions."""
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        dev_role = next(r for r in DEFAULT_ROLES if r["name"] == "developer")

        assert "projects:create:any" in dev_role["permissions"]
        assert "projects:read:any" in dev_role["permissions"]

    def test_viewer_role_is_read_only(self) -> None:
        """Test that viewer role only has read permissions."""
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        viewer_role = next(r for r in DEFAULT_ROLES if r["name"] == "viewer")

        for perm in viewer_role["permissions"]:
            assert ":read:" in perm

    def test_guest_role_has_no_permissions(self) -> None:
        """Test that guest role has no permissions."""
        from sdlc_agent.db.rbac_seed import DEFAULT_ROLES

        guest_role = next(r for r in DEFAULT_ROLES if r["name"] == "guest")

        assert guest_role["permissions"] == []
