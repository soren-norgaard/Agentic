# =============================================================================
# SDLC Agent - RBAC Pydantic Schemas
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator

from sdlc_agent.db.rbac_models import AuditAction, RoleType, UserStatus


# =============================================================================
# User Schemas
# =============================================================================


class UserBase(BaseModel):
    """Base schema for user data."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=500)
    status: UserStatus | None = None


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """Schema for user response."""

    id: uuid.UUID
    email: str
    username: str
    full_name: str
    avatar_url: str | None
    status: UserStatus
    is_superuser: bool
    email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at", "last_login_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class UserWithRolesResponse(UserResponse):
    """User response including roles."""

    roles: list["RoleResponse"] = []


class UserListResponse(BaseModel):
    """Schema for paginated user list."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Role Schemas
# =============================================================================


class RoleBase(BaseModel):
    """Base schema for role data."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)


class RoleCreate(RoleBase):
    """Schema for creating a role."""

    priority: int = Field(0, ge=0, le=100)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    priority: int | None = Field(None, ge=0, le=100)
    is_active: bool | None = None


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: uuid.UUID
    name: str
    description: str | None
    role_type: RoleType
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


class RoleWithPermissionsResponse(RoleResponse):
    """Role response including permissions."""

    permissions: list["PermissionResponse"] = []


class RoleListResponse(BaseModel):
    """Schema for paginated role list."""

    items: list[RoleResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Permission Schemas
# =============================================================================


class PermissionBase(BaseModel):
    """Base schema for permission data."""

    code: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z_]+:[a-z_*]+:[a-z_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class PermissionCreate(PermissionBase):
    """Schema for creating a permission."""

    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    scope: str = Field("own", min_length=1, max_length=20)


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class PermissionResponse(BaseModel):
    """Schema for permission response."""

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    resource: str
    action: str
    scope: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


class PermissionListResponse(BaseModel):
    """Schema for paginated permission list."""

    items: list[PermissionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Assignment Schemas
# =============================================================================


class UserRoleAssign(BaseModel):
    """Schema for assigning a role to a user."""

    role_id: uuid.UUID
    expires_at: datetime | None = None


class UserRoleResponse(BaseModel):
    """Schema for user-role assignment response."""

    user_id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    assigned_by: str | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at", "expires_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class RolePermissionAssign(BaseModel):
    """Schema for assigning a permission to a role."""

    permission_id: uuid.UUID


class RolePermissionResponse(BaseModel):
    """Schema for role-permission assignment response."""

    role_id: uuid.UUID
    permission_id: uuid.UUID
    permission_code: str
    granted_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


# =============================================================================
# Authentication Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetResponse(BaseModel):
    """Schema for password reset response."""

    message: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # user_id
    email: str
    username: str
    roles: list[str]
    permissions: list[str]
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID for revocation


# =============================================================================
# Audit Log Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_type: str
    action: AuditAction
    resource_type: str
    resource_id: str | None
    details: dict
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime

    class Config:
        from_attributes = True

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""

    actor_id: uuid.UUID | None = None
    action: AuditAction | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None


# Update forward references
UserWithRolesResponse.model_rebuild()
RoleWithPermissionsResponse.model_rebuild()
