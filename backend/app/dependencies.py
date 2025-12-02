"""
PaperTrading Platform - Dependencies
Dependency injection for FastAPI endpoints
"""
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session_maker
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.core.security import verify_token


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    """
    User repository dependency.
    
    Args:
        db: Database session
        
    Returns:
        UserRepository instance
    """
    return UserRepository(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        user_repo: User repository
        
    Returns:
        Current User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token and extract user_id
    user_id = verify_token(token, token_type="access")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    try:
        user = await user_repo.get_by_id(int(user_id))
    except (ValueError, TypeError):
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active User object
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superuser.
    
    Args:
        current_user: Current active user
        
    Returns:
        Current superuser User object
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


def get_optional_current_user(
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(
            tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
            auto_error=False
        )
    ),
) -> Optional[User]:
    """
    Get current user if token is provided (optional authentication).
    
    Args:
        token: Optional JWT access token
        
    Returns:
        User object if authenticated, None otherwise
    """
    if token is None:
        return None
    
    user_id = verify_token(token, token_type="access")
    if user_id is None:
        return None
    
    # Note: This is a sync function, so we can't query DB here
    # For optional auth, we return just the user_id
    return None  # TODO: Implement async optional auth if needed
