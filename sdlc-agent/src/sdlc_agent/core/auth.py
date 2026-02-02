# =============================================================================
# SDLC Agent - Authentication Utilities
# =============================================================================

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.exceptions import AuthenticationError, AuthorizationError


# =============================================================================
# Password Hashing
# =============================================================================

# Configure bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Management
# =============================================================================

# Token settings
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str  # user_id
    email: str
    username: str
    roles: list[str]
    permissions: list[str]
    exp: datetime
    iat: datetime
    jti: str  # unique token ID


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    username: str,
    roles: list[str],
    permissions: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new JWT access token.

    Args:
        user_id: User's UUID
        email: User's email
        username: User's username
        roles: List of role names
        permissions: List of permission codes
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        "sub": str(user_id),
        "email": email,
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }

    return jwt.encode(payload, get_settings().auth.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new JWT refresh token.

    Args:
        user_id: User's UUID
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }

    return jwt.encode(payload, get_settings().auth.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, get_settings().auth.jwt_secret_key.get_secret_value(), algorithms=[ALGORITHM])
        return payload
    except PyJWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def verify_access_token(token: str) -> TokenData:
    """Verify an access token and return its data.

    Args:
        token: JWT access token string

    Returns:
        TokenData with user information

    Raises:
        AuthenticationError: If token is invalid, expired, or not an access token
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    return TokenData(
        sub=payload["sub"],
        email=payload["email"],
        username=payload["username"],
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        jti=payload["jti"],
    )


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Verify a refresh token.

    Args:
        token: JWT refresh token string

    Returns:
        Token payload with user_id

    Raises:
        AuthenticationError: If token is invalid, expired, or not a refresh token
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type")

    return payload


# =============================================================================
# Permission Checking
# =============================================================================


def check_permission(
    user_permissions: set[str],
    required_permission: str,
) -> bool:
    """Check if user has the required permission.

    Supports wildcard matching:
        - "*" matches everything (superuser)
        - "resource:*:scope" matches any action
        - "resource:action:any" matches own and any scope

    Args:
        user_permissions: Set of user's permission codes
        required_permission: Permission code to check

    Returns:
        True if user has permission, False otherwise
    """
    # Superuser has all permissions
    if "*" in user_permissions:
        return True

    # Direct match
    if required_permission in user_permissions:
        return True

    # Parse required permission
    parts = required_permission.split(":")
    if len(parts) != 3:
        return False

    resource, action, scope = parts

    # Check wildcard action (e.g., "projects:*:any")
    wildcard_action = f"{resource}:*:{scope}"
    if wildcard_action in user_permissions:
        return True

    # Check any scope includes own (e.g., "projects:read:any" includes "projects:read:own")
    if scope == "own":
        any_scope = f"{resource}:{action}:any"
        if any_scope in user_permissions:
            return True

        # Also check wildcard with any
        wildcard_any = f"{resource}:*:any"
        if wildcard_any in user_permissions:
            return True

    return False


def require_permission(
    user_permissions: set[str],
    required_permission: str,
) -> None:
    """Require that user has the specified permission.

    Args:
        user_permissions: Set of user's permission codes
        required_permission: Permission code to require

    Raises:
        AuthorizationError: If user lacks the required permission
    """
    if not check_permission(user_permissions, required_permission):
        raise AuthorizationError(
            f"Permission denied: requires '{required_permission}'"
        )


def require_any_permission(
    user_permissions: set[str],
    required_permissions: list[str],
) -> None:
    """Require that user has at least one of the specified permissions.

    Args:
        user_permissions: Set of user's permission codes
        required_permissions: List of permission codes (any one is sufficient)

    Raises:
        AuthorizationError: If user lacks all required permissions
    """
    for perm in required_permissions:
        if check_permission(user_permissions, perm):
            return

    raise AuthorizationError(
        f"Permission denied: requires one of {required_permissions}"
    )


def require_all_permissions(
    user_permissions: set[str],
    required_permissions: list[str],
) -> None:
    """Require that user has all of the specified permissions.

    Args:
        user_permissions: Set of user's permission codes
        required_permissions: List of permission codes (all required)

    Raises:
        AuthorizationError: If user lacks any required permission
    """
    for perm in required_permissions:
        require_permission(user_permissions, perm)
