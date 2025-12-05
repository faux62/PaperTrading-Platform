"""
PaperTrading Platform - Security Module
JWT Authentication, Password Hashing, Token Management
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Annotated
import uuid

import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings


# JWT Settings
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The hashed password string
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
    jti: Optional[str] = None
) -> tuple[str, str]:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user_id or email)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional claims to include in token
        jti: Optional JWT ID for token tracking (auto-generated if not provided)
        
    Returns:
        Tuple of (encoded JWT token string, jti)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    token_jti = jti or str(uuid.uuid4())
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": token_jti
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=ALGORITHM
    )
    return encoded_jwt, token_jti


def create_refresh_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> tuple[str, str]:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user_id or email)
        expires_delta: Optional custom expiration time
        jti: Optional JWT ID for token tracking (auto-generated if not provided)
        
    Returns:
        Tuple of (encoded JWT refresh token string, jti)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    token_jti = jti or str(uuid.uuid4())
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": token_jti
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=ALGORITHM
    )
    return encoded_jwt, token_jti


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string to decode
        
    Returns:
        Decoded token payload as dict, or None if invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify a JWT token and return the subject.
    
    Args:
        token: The JWT token string to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Subject (user_id) if token is valid, None otherwise
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check token type
    if payload.get("type") != token_type:
        return None
    
    # Check expiration
    exp = payload.get("exp")
    if exp is None:
        return None
    
    if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        return None
    
    return payload.get("sub")


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
):
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        token: JWT token extracted from Authorization header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.db.models.user import User
    from app.db.database import async_session_maker
    from sqlalchemy import select
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(token, "access")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.id == int(user_id))
        )
        user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user
