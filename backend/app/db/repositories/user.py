"""
PaperTrading Platform - User Repository
CRUD operations for User model
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserRepository:
    """Repository for User CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: The user's ID
            
        Returns:
            User object if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: The user's email address
            
        Returns:
            User object if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: The user's username
            
        Returns:
            User object if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email_or_username(
        self, 
        email: str, 
        username: str
    ) -> Optional[User]:
        """
        Get user by email or username.
        
        Args:
            email: Email address to search
            username: Username to search
            
        Returns:
            User object if found by either field, None otherwise
        """
        result = await self.session.execute(
            select(User).where(
                or_(User.email == email, User.username == username)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """
        Get all users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of User objects
        """
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created User object
        """
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
            is_superuser=False,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(
        self, 
        user: User, 
        user_data: UserUpdate
    ) -> User:
        """
        Update an existing user.
        
        Args:
            user: The user to update
            user_data: New user data
            
        Returns:
            Updated User object
        """
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Hash password if being updated
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user: User) -> bool:
        """
        Delete a user.
        
        Args:
            user: The user to delete
            
        Returns:
            True if deleted successfully
        """
        await self.session.delete(user)
        await self.session.commit()
        return True
    
    async def authenticate(
        self, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def update_last_login(self, user: User) -> User:
        """
        Update user's last login timestamp.
        
        Args:
            user: The user to update
            
        Returns:
            Updated User object
        """
        user.last_login = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def is_active(self, user: User) -> bool:
        """
        Check if user is active.
        
        Args:
            user: The user to check
            
        Returns:
            True if user is active
        """
        return user.is_active
    
    async def is_superuser(self, user: User) -> bool:
        """
        Check if user is a superuser.
        
        Args:
            user: The user to check
            
        Returns:
            True if user is a superuser
        """
        return user.is_superuser
