"""
Unit Tests - Pydantic Schemas
Tests for request/response schema validation.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    User,
    UserInDB,
    Token,
    TokenPayload,
    RefreshTokenRequest,
    Message,
    ErrorResponse
)


class TestUserCreate:
    """Tests for UserCreate schema."""
    
    def test_valid_user_create(self):
        """Valid data should create UserCreate successfully."""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        user = UserCreate(**data)
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password == "SecurePassword123!"
        assert user.full_name == "Test User"
    
    def test_user_create_without_full_name(self):
        """UserCreate should work without full_name."""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePassword123!"
        }
        user = UserCreate(**data)
        assert user.full_name is None
    
    def test_user_create_invalid_email(self):
        """Invalid email should raise ValidationError."""
        data = {
            "email": "not-an-email",
            "username": "testuser",
            "password": "SecurePassword123!"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "email" in str(exc_info.value).lower()
    
    def test_user_create_short_username(self):
        """Username shorter than 3 chars should raise ValidationError."""
        data = {
            "email": "test@example.com",
            "username": "ab",
            "password": "SecurePassword123!"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "username" in str(exc_info.value).lower()
    
    def test_user_create_long_username(self):
        """Username longer than 50 chars should raise ValidationError."""
        data = {
            "email": "test@example.com",
            "username": "a" * 51,
            "password": "SecurePassword123!"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "username" in str(exc_info.value).lower()
    
    def test_user_create_short_password(self):
        """Password shorter than 8 chars should raise ValidationError."""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "short"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "password" in str(exc_info.value).lower()
    
    def test_user_create_long_password(self):
        """Password longer than 100 chars should raise ValidationError."""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "a" * 101
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "password" in str(exc_info.value).lower()
    
    def test_user_create_missing_required_fields(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com")


class TestUserLogin:
    """Tests for UserLogin schema."""
    
    def test_valid_login(self):
        """Valid login data should work."""
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        login = UserLogin(**data)
        assert login.email == "test@example.com"
        assert login.password == "password123"
    
    def test_login_invalid_email(self):
        """Invalid email should raise ValidationError."""
        data = {
            "email": "invalid",
            "password": "password123"
        }
        with pytest.raises(ValidationError):
            UserLogin(**data)
    
    def test_login_missing_password(self):
        """Missing password should raise ValidationError."""
        with pytest.raises(ValidationError):
            UserLogin(email="test@example.com")


class TestUserUpdate:
    """Tests for UserUpdate schema."""
    
    def test_update_all_fields(self):
        """All fields should be updateable."""
        data = {
            "email": "new@example.com",
            "username": "newuser",
            "full_name": "New Name",
            "password": "NewPassword123!"
        }
        update = UserUpdate(**data)
        assert update.email == "new@example.com"
        assert update.username == "newuser"
    
    def test_update_partial(self):
        """Partial updates should work."""
        update = UserUpdate(full_name="Just Name")
        assert update.full_name == "Just Name"
        assert update.email is None
        assert update.username is None
        assert update.password is None
    
    def test_update_empty(self):
        """Empty update should be valid."""
        update = UserUpdate()
        assert update.email is None
        assert update.username is None


class TestUserSchema:
    """Tests for User response schema."""
    
    def test_user_from_dict(self):
        """User should be creatable from dict."""
        data = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        user = User(**data)
        assert user.id == 1
        assert user.email == "test@example.com"
    
    def test_user_excludes_password(self):
        """User schema should not include password field."""
        data = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow()
        }
        user = User(**data)
        assert not hasattr(user, "password")
        assert not hasattr(user, "hashed_password")


class TestUserInDB:
    """Tests for UserInDB schema."""
    
    def test_user_in_db_includes_password(self):
        """UserInDB should include hashed_password."""
        data = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hash",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow()
        }
        user = UserInDB(**data)
        assert user.hashed_password == "$2b$12$hash"


class TestTokenSchemas:
    """Tests for token-related schemas."""
    
    def test_token_schema(self):
        """Token schema should work correctly."""
        token = Token(
            access_token="access123",
            refresh_token="refresh456",
            token_type="bearer"
        )
        assert token.access_token == "access123"
        assert token.refresh_token == "refresh456"
        assert token.token_type == "bearer"
    
    def test_token_default_type(self):
        """Token type should default to bearer."""
        token = Token(access_token="a", refresh_token="r")
        assert token.token_type == "bearer"
    
    def test_token_payload_schema(self):
        """TokenPayload should parse correctly."""
        now = datetime.utcnow()
        payload = TokenPayload(
            sub="user123",
            exp=now,
            iat=now,
            type="access"
        )
        assert payload.sub == "user123"
        assert payload.type == "access"
    
    def test_refresh_token_request(self):
        """RefreshTokenRequest should work."""
        request = RefreshTokenRequest(refresh_token="token123")
        assert request.refresh_token == "token123"


class TestMessageSchemas:
    """Tests for message schemas."""
    
    def test_message_schema(self):
        """Message schema should work."""
        msg = Message(message="Success!")
        assert msg.message == "Success!"
    
    def test_error_response(self):
        """ErrorResponse should work."""
        error = ErrorResponse(detail="Something went wrong", code="ERR001")
        assert error.detail == "Something went wrong"
        assert error.code == "ERR001"
    
    def test_error_response_optional_code(self):
        """ErrorResponse code should be optional."""
        error = ErrorResponse(detail="Error occurred")
        assert error.detail == "Error occurred"
        assert error.code is None
