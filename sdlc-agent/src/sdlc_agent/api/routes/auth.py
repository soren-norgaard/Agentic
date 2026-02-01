# =============================================================================
# SDLC Agent - Authentication Routes
# =============================================================================

from __future__ import annotations

from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sdlc_agent.api.schemas.rbac import (
    LoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from sdlc_agent.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from sdlc_agent.core.exceptions import AuthenticationError
from sdlc_agent.core.logging import get_logger
from sdlc_agent.db import get_session
from sdlc_agent.db.rbac_models import (
    AuditAction,
    RBACAuditLog,
    User,
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
        selectinload(User.user_roles).selectinload("role").selectinload("role_permissions").selectinload("permission")
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
        selectinload(User.user_roles).selectinload("role").selectinload("role_permissions").selectinload("permission")
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
