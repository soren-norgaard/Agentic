# =============================================================================
# SDLC Agent - Authentication Routes
# =============================================================================

from __future__ import annotations

from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sdlc_agent.api.schemas.rbac import (
    ForgotPasswordRequest,
    LoginRequest,
    PasswordResetResponse,
    ResetPasswordRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from sdlc_agent.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)
from sdlc_agent.core.exceptions import AuthenticationError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import (
    AuditAction,
    RBACAuditLog,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)

router = APIRouter()
logger = get_logger(__name__)


async def _log_audit(
    session: AsyncSession,
    action: AuditAction,
    actor_id: str | None,
    actor_email: str | None,
    resource_type: str,
    resource_id: str | None,
    details: dict,
    request: Request,
) -> None:
    """Log an audit event."""
    log = RBACAuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        actor_type="user" if actor_id else "system",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(log)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    login_data: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate user and return JWT tokens.

    Args:
        login_data: Username and password

    Returns:
        Access and refresh tokens

    Raises:
        AuthenticationError: If credentials are invalid
    """
    # Find user by username or email
    query = select(User).where(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).options(
        selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        await _log_audit(
            session=session,
            action=AuditAction.LOGIN_FAILED,
            actor_id=None,
            actor_email=login_data.username,
            resource_type="auth",
            resource_id=None,
            details={"reason": "user_not_found"},
            request=request,
        )
        await session.commit()
        raise AuthenticationError("Invalid username or password")

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(UTC):
        await _log_audit(
            session=session,
            action=AuditAction.LOGIN_FAILED,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="auth",
            resource_id=str(user.id),
            details={"reason": "account_locked"},
            request=request,
        )
        await session.commit()
        raise AuthenticationError("Account is temporarily locked")

    # Check account status
    if user.status != UserStatus.ACTIVE:
        await _log_audit(
            session=session,
            action=AuditAction.LOGIN_FAILED,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="auth",
            resource_id=str(user.id),
            details={"reason": f"account_{user.status.value}"},
            request=request,
        )
        await session.commit()
        raise AuthenticationError(f"Account is {user.status.value}")

    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            from datetime import timedelta
            user.locked_until = datetime.now(UTC) + timedelta(minutes=15)

        await _log_audit(
            session=session,
            action=AuditAction.LOGIN_FAILED,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="auth",
            resource_id=str(user.id),
            details={"reason": "invalid_password", "attempts": user.failed_login_attempts},
            request=request,
        )
        await session.commit()
        raise AuthenticationError("Invalid username or password")

    # Successful login - reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = request.client.host if request.client else None

    # Get roles and permissions
    roles = [ur.role.name for ur in user.user_roles if ur.role.is_active]
    permissions = list(user.permissions)

    # Create tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        username=user.username,
        roles=roles,
        permissions=permissions,
    )
    refresh_token = create_refresh_token(user_id=user.id)

    await _log_audit(
        session=session,
        action=AuditAction.LOGIN,
        actor_id=str(user.id),
        actor_email=user.email,
        resource_type="auth",
        resource_id=str(user.id),
        details={"roles": roles},
        request=request,
    )
    await session.commit()

    logger.info(f"User {user.username} logged in successfully")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request,
    refresh_data: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token

    Returns:
        New access and refresh tokens

    Raises:
        AuthenticationError: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_refresh_token(refresh_data.refresh_token)
    user_id = payload["sub"]

    # Get user with roles and permissions
    query = select(User).where(User.id == user_id).options(
        selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        raise AuthenticationError("Invalid refresh token")

    # Get roles and permissions
    roles = [ur.role.name for ur in user.user_roles if ur.role.is_active]
    permissions = list(user.permissions)

    # Create new tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        username=user.username,
        roles=roles,
        permissions=permissions,
    )
    new_refresh_token = create_refresh_token(user_id=user.id)

    await _log_audit(
        session=session,
        action=AuditAction.TOKEN_REFRESHED,
        actor_id=str(user.id),
        actor_email=user.email,
        resource_type="auth",
        resource_id=str(user.id),
        details={},
        request=request,
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Logout and invalidate tokens.

    Note: In a production system, you would add the token JTI to a blacklist
    stored in Redis. For now, we just log the logout event.
    """
    # In production, extract user from current token and blacklist JTI
    # For now, just log the logout attempt
    logger.info("User logged out")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserResponse:
    """Get the current authenticated user's information.

    Returns:
        Current user details

    Raises:
        AuthenticationError: If not authenticated
    """
    from sdlc_agent.api.routes.rbac_deps import get_current_user
    
    if not authorization:
        raise AuthenticationError("Missing authorization header")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    token = parts[1]

    # Verify token and get user
    token_data = verify_access_token(token)

    # Get user from database
    query = select(User).where(User.id == token_data.sub).options(
        selectinload(User.user_roles)
        .selectinload(UserRole.role)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError(f"Account is {user.status.value}")

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        status=user.status,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/forgot-password", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PasswordResetResponse:
    """Request a password reset.

    Generates a password reset token and would typically send it via email.
    For security, always returns success even if email doesn't exist.

    Args:
        forgot_data: Email address for password reset

    Returns:
        Success message (always, for security)
    """
    import secrets
    from datetime import timedelta

    # Find user by email
    result = await session.execute(
        select(User).where(User.email == forgot_data.email)
    )
    user = result.scalar_one_or_none()

    if user and user.status == UserStatus.ACTIVE:
        # Generate reset token (in production, store this in DB/Redis with expiry)
        reset_token = secrets.token_urlsafe(32)

        # Store token hash in user record (or separate tokens table)
        # For now, we'll use a simple approach with password_reset_token field
        # In production, use a dedicated tokens table with expiry
        user.password_reset_token = hash_password(reset_token)
        user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)

        await _log_audit(
            session=session,
            action=AuditAction.PASSWORD_RESET_REQUESTED,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="auth",
            resource_id=str(user.id),
            details={"email": forgot_data.email},
            request=request,
        )
        await session.commit()

        # In production, send email with reset link containing the token
        # Example: f"{FRONTEND_URL}/reset-password?token={reset_token}"
        logger.info(f"Password reset requested for {forgot_data.email}")
        logger.debug(f"Reset token (dev only): {reset_token}")
    else:
        # Log attempt for non-existent email (for monitoring)
        logger.info(f"Password reset requested for unknown email: {forgot_data.email}")

    # Always return success for security (don't reveal if email exists)
    return PasswordResetResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PasswordResetResponse:
    """Reset password using a reset token.

    Args:
        reset_data: Reset token and new password

    Returns:
        Success message

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    # Find users with password reset pending
    result = await session.execute(
        select(User).where(
            User.password_reset_token.isnot(None),
            User.password_reset_expires > datetime.now(UTC),
        )
    )
    users = result.scalars().all()

    # Find user with matching token
    matching_user = None
    for user in users:
        if verify_password(reset_data.token, user.password_reset_token):
            matching_user = user
            break

    if not matching_user:
        await _log_audit(
            session=session,
            action=AuditAction.PASSWORD_RESET_FAILED,
            actor_id=None,
            actor_email=None,
            resource_type="auth",
            resource_id=None,
            details={"reason": "invalid_or_expired_token"},
            request=request,
        )
        await session.commit()
        raise AuthenticationError("Invalid or expired reset token")

    # Update password
    matching_user.password_hash = hash_password(reset_data.new_password)
    matching_user.password_reset_token = None
    matching_user.password_reset_expires = None
    matching_user.failed_login_attempts = 0
    matching_user.locked_until = None

    await _log_audit(
        session=session,
        action=AuditAction.PASSWORD_RESET_COMPLETED,
        actor_id=str(matching_user.id),
        actor_email=matching_user.email,
        resource_type="auth",
        resource_id=str(matching_user.id),
        details={},
        request=request,
    )
    await session.commit()

    logger.info(f"Password reset completed for {matching_user.email}")

    return PasswordResetResponse(
        message="Password has been reset successfully. You can now log in with your new password."
    )
