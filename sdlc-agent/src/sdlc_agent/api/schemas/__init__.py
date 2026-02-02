# =============================================================================
# SDLC Agent - API Schemas
# =============================================================================

from sdlc_agent.api.schemas.rbac import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    LoginRequest,
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
    RoleCreate,
    RoleListResponse,
    RolePermissionAssign,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
    RoleWithPermissionsResponse,
    TokenPayload,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserResponse,
    UserRoleAssign,
    UserRoleResponse,
    UserUpdate,
    UserWithRolesResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserResponse",
    "UserWithRolesResponse",
    "UserListResponse",
    # Role schemas
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleWithPermissionsResponse",
    "RoleListResponse",
    # Permission schemas
    "PermissionCreate",
    "PermissionUpdate",
    "PermissionResponse",
    "PermissionListResponse",
    # Assignment schemas
    "UserRoleAssign",
    "UserRoleResponse",
    "RolePermissionAssign",
    "RolePermissionResponse",
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenPayload",
    # Audit schemas
    "AuditLogResponse",
    "AuditLogListResponse",
    "AuditLogFilter",
]
