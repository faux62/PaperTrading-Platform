"""
PaperTrading Platform - Authentication Endpoints
With Redis Session Management and Token Blacklisting
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_user_repository,
    get_current_active_user,
    get_db,
)
from app.db.repositories.user import UserRepository
from app.db.models.user import User
from app.db.redis_client import redis_client
from app.schemas.user import (
    UserCreate,
    UserLogin,
    User as UserSchema,
    UserWithToken,
    Token,
    RefreshTokenRequest,
    Message,
    PasswordChange,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings

router = APIRouter()


def get_client_info(request: Request) -> dict:
    """Extract client information from request for session tracking."""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }


@router.post(
    "/register",
    response_model=UserWithToken,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and return user data with access tokens."
)
async def register(
    request: Request,
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserWithToken:
    """
    Register a new user.
    
    - **email**: Valid email address (unique)
    - **username**: Username (3-50 chars, unique)
    - **password**: Password (min 8 chars)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    existing_user = await user_repo.get_by_email_or_username(
        email=user_data.email,
        username=user_data.username
    )
    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = await user_repo.create(user_data)
    
    # Generate tokens with JTI
    access_token, access_jti = create_access_token(subject=user.id)
    refresh_token, refresh_jti = create_refresh_token(subject=user.id)
    
    # Store session and refresh token in Redis
    client_info = get_client_info(request)
    await redis_client.create_session(
        user_id=user.id,
        session_id=access_jti,
        data={
            "refresh_jti": refresh_jti,
            **client_info
        },
        ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    await redis_client.store_refresh_token(
        user_id=user.id,
        token_jti=refresh_jti,
        ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return UserWithToken(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token",
    description="Authenticate with email and password to receive access and refresh tokens."
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Token:
    """
    OAuth2 compatible token login.
    
    - **username**: User's email address or username
    - **password**: User's password
    """
    # Authenticate user (username field can contain email or username)
    user = await user_repo.authenticate(
        email_or_username=form_data.username,
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Update last login
    await user_repo.update_last_login(user)
    
    # Generate tokens with JTI
    access_token, access_jti = create_access_token(subject=user.id)
    refresh_token, refresh_jti = create_refresh_token(subject=user.id)
    
    # Store session and refresh token in Redis
    client_info = get_client_info(request)
    await redis_client.create_session(
        user_id=user.id,
        session_id=access_jti,
        data={
            "refresh_jti": refresh_jti,
            **client_info
        },
        ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    await redis_client.store_refresh_token(
        user_id=user.id,
        token_jti=refresh_jti,
        ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # Track user activity
    await redis_client.update_user_activity(user.id, "login")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login/json",
    response_model=Token,
    summary="Login with JSON body",
    description="Authenticate with JSON body containing email/username and password."
)
async def login_json(
    request: Request,
    credentials: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository)
) -> Token:
    """
    JSON login endpoint (alternative to OAuth2 form).
    
    - **email_or_username**: User's email address or username
    - **password**: User's password
    """
    user = await user_repo.authenticate(
        email_or_username=credentials.email_or_username,
        password=credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Update last login
    await user_repo.update_last_login(user)
    
    # Generate tokens with JTI
    access_token, access_jti = create_access_token(subject=user.id)
    refresh_token, refresh_jti = create_refresh_token(subject=user.id)
    
    # Store session and refresh token in Redis
    client_info = get_client_info(request)
    await redis_client.create_session(
        user_id=user.id,
        session_id=access_jti,
        data={
            "refresh_jti": refresh_jti,
            **client_info
        },
        ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    await redis_client.store_refresh_token(
        user_id=user.id,
        token_jti=refresh_jti,
        ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # Track user activity
    await redis_client.update_user_activity(user.id, "login")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token."
)
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repository)
) -> Token:
    """
    Refresh access token.
    
    - **refresh_token**: Valid refresh token
    """
    # Decode and verify refresh token
    payload = decode_token(token_request.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    refresh_jti = payload.get("jti")
    
    if not user_id or not refresh_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Check if refresh token is still valid in Redis
    token_data = await redis_client.validate_refresh_token(refresh_jti)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )
    
    # Get user
    try:
        user = await user_repo.get_by_id(int(user_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Revoke old refresh token
    await redis_client.revoke_refresh_token(refresh_jti, user.id)
    
    # Generate new tokens with JTI
    new_access_token, new_access_jti = create_access_token(subject=user.id)
    new_refresh_token, new_refresh_jti = create_refresh_token(subject=user.id)
    
    # Store new session and refresh token in Redis
    client_info = get_client_info(request)
    await redis_client.create_session(
        user_id=user.id,
        session_id=new_access_jti,
        data={
            "refresh_jti": new_refresh_jti,
            **client_info
        },
        ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    await redis_client.store_refresh_token(
        user_id=user.id,
        token_jti=new_refresh_jti,
        ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post(
    "/logout",
    response_model=Message,
    summary="Logout user",
    description="Logout the current user and invalidate their tokens."
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Message:
    """
    Logout current user.
    
    Invalidates the current session and blacklists the access token.
    """
    # Get authorization header to extract token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        
        if payload:
            access_jti = payload.get("jti")
            if access_jti:
                # Delete the session
                await redis_client.delete_session(current_user.id, access_jti)
                
                # Blacklist the token for its remaining lifetime
                exp = payload.get("exp")
                if exp:
                    import time
                    ttl = max(int(exp - time.time()), 0)
                    await redis_client.blacklist_token(access_jti, current_user.id, ttl)
    
    # Track activity
    await redis_client.update_user_activity(current_user.id, "logout")
    
    return Message(message="Successfully logged out")


@router.post(
    "/logout/all",
    response_model=Message,
    summary="Logout from all devices",
    description="Logout the current user from all devices by invalidating all sessions."
)
async def logout_all(
    current_user: User = Depends(get_current_active_user)
) -> Message:
    """
    Logout from all devices.
    
    Invalidates all sessions and refresh tokens for the user.
    """
    # Delete all sessions
    sessions_deleted = await redis_client.delete_all_user_sessions(current_user.id)
    
    # Revoke all refresh tokens
    tokens_revoked = await redis_client.revoke_all_refresh_tokens(current_user.id)
    
    # Track activity
    await redis_client.update_user_activity(current_user.id, "logout_all")
    
    return Message(
        message=f"Successfully logged out from all devices. "
                f"Sessions cleared: {sessions_deleted}, Tokens revoked: {tokens_revoked}"
    )


@router.get(
    "/sessions",
    summary="Get active sessions",
    description="Get all active sessions for the current user."
)
async def get_sessions(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get all active sessions for the current user.
    
    Returns a list of active session IDs and their details.
    """
    session_ids = await redis_client.get_user_sessions(current_user.id)
    
    sessions = []
    for session_id in session_ids:
        session_data = await redis_client.get_session(current_user.id, session_id)
        if session_data:
            sessions.append({
                "session_id": session_id,
                **session_data
            })
    
    return {
        "user_id": current_user.id,
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@router.delete(
    "/sessions/{session_id}",
    response_model=Message,
    summary="Revoke specific session",
    description="Revoke a specific session by its ID."
)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Message:
    """
    Revoke a specific session.
    
    - **session_id**: The session ID to revoke
    """
    deleted = await redis_client.delete_session(current_user.id, session_id)
    
    if deleted:
        return Message(message=f"Session {session_id} has been revoked")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Get current user",
    description="Get the current authenticated user's information."
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserSchema:
    """
    Get current user info.
    
    Returns the authenticated user's profile information.
    """
    # Track user activity
    await redis_client.update_user_activity(current_user.id, "profile_view")
    
    return UserSchema(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        base_currency=getattr(current_user, 'base_currency', 'USD'),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.patch(
    "/me",
    response_model=UserSchema,
    summary="Update current user preferences",
    description="Update the current user's preferences including base currency."
)
async def update_current_user(
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserSchema:
    """
    Update current user preferences.
    
    - **base_currency**: Set preferred base currency (USD, EUR, GBP, etc.)
    - **full_name**: Update display name
    """
    allowed_fields = {'base_currency', 'full_name'}
    valid_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}
    
    # Filter to allowed fields
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    # Validate base_currency
    if 'base_currency' in filtered_updates:
        if filtered_updates['base_currency'] not in valid_currencies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid currency. Supported: {', '.join(valid_currencies)}"
            )
    
    if filtered_updates:
        updated_user = await user_repo.update_preferences(current_user.id, filtered_updates)
        if updated_user:
            current_user = updated_user
    
    return UserSchema(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        base_currency=getattr(current_user, 'base_currency', 'USD'),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.get(
    "/sessions",
    summary="Get active sessions",
    description="Get list of active sessions for the current user."
)
async def get_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all active sessions for the current user.
    
    Returns list of sessions with device info and creation time.
    """
    session_ids = await redis_client.get_user_sessions(current_user.id)
    
    sessions = []
    for session_id in session_ids:
        session_data = await redis_client.get_session(current_user.id, session_id)
        if session_data:
            sessions.append({
                "id": session_id,
                "ip": session_data.get("ip", "unknown"),
                "user_agent": session_data.get("user_agent", "unknown"),
                "created_at": session_data.get("created_at"),
                "current": False,  # Will be set client-side based on token
            })
    
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.delete(
    "/sessions/{session_id}",
    summary="Revoke a session",
    description="Revoke a specific session (logout from a device)."
)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Revoke a specific session.
    
    - **session_id**: The session ID to revoke
    
    Returns success message.
    """
    deleted = await redis_client.delete_session(current_user.id, session_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {"message": "Session revoked successfully"}


@router.post(
    "/change-password",
    response_model=Message,
    summary="Change password",
    description="Change the current user's password. Requires current password verification."
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db)
) -> Message:
    """
    Change current user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (min 8 chars)
    
    Returns success message or error if current password is incorrect.
    """
    from datetime import datetime
    from app.db.models.user_settings import UserSettings
    from sqlalchemy import select
    
    success, message = await user_repo.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password_changed_at in user_settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if settings:
        settings.password_changed_at = datetime.utcnow()
        await db.commit()
    else:
        # Create settings record if not exists
        settings = UserSettings(user_id=current_user.id, password_changed_at=datetime.utcnow())
        db.add(settings)
        await db.commit()
    
    # Optionally invalidate all other sessions after password change
    await redis_client.delete_all_user_sessions(current_user.id)
    
    return Message(message=message)

