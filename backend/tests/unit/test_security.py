"""
Unit Tests - Core Security Module
Tests for JWT tokens, password hashing, and authentication.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import os

# Set test environment before importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing"

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    ALGORITHM
)


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_get_password_hash_returns_string(self):
        """Password hash should return a string."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_get_password_hash_different_from_plain(self):
        """Hashed password should be different from plain password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed != password
    
    def test_get_password_hash_unique_per_call(self):
        """Each hash should be unique due to salt."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Verify should return True for correct password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Verify should return False for incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty(self):
        """Verify should handle empty password."""
        password = ""
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False
    
    def test_verify_password_special_chars(self):
        """Verify should handle special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_unicode(self):
        """Verify should handle unicode characters."""
        password = "Pässwörd123日本語"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestAccessToken:
    """Tests for access token creation and validation."""
    
    def test_create_access_token_returns_tuple(self):
        """create_access_token should return (token, jti) tuple."""
        result = create_access_token(subject="user123")
        assert isinstance(result, tuple)
        assert len(result) == 2
        token, jti = result
        assert isinstance(token, str)
        assert isinstance(jti, str)
    
    def test_create_access_token_valid_jwt(self):
        """Token should be a valid JWT with three parts."""
        token, _ = create_access_token(subject="user123")
        parts = token.split(".")
        assert len(parts) == 3
    
    def test_create_access_token_can_be_decoded(self):
        """Token should be decodable."""
        subject = "user123"
        token, jti = create_access_token(subject=subject)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert payload["jti"] == jti
    
    def test_create_access_token_custom_expiry(self):
        """Token should use custom expiry when provided."""
        token, _ = create_access_token(
            subject="user123",
            expires_delta=timedelta(hours=2)
        )
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Should expire in about 2 hours (with some tolerance)
        delta = exp - now
        assert timedelta(hours=1, minutes=55) < delta < timedelta(hours=2, minutes=5)
    
    def test_create_access_token_additional_claims(self):
        """Token should include additional claims."""
        token, _ = create_access_token(
            subject="user123",
            additional_claims={"role": "admin", "tenant": "org1"}
        )
        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["tenant"] == "org1"
    
    def test_create_access_token_custom_jti(self):
        """Token should use custom JTI when provided."""
        custom_jti = "custom-token-id-12345"
        token, jti = create_access_token(subject="user123", jti=custom_jti)
        assert jti == custom_jti
        payload = decode_token(token)
        assert payload["jti"] == custom_jti


class TestRefreshToken:
    """Tests for refresh token creation and validation."""
    
    def test_create_refresh_token_returns_tuple(self):
        """create_refresh_token should return (token, jti) tuple."""
        result = create_refresh_token(subject="user123")
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_create_refresh_token_type(self):
        """Refresh token should have type 'refresh'."""
        token, _ = create_refresh_token(subject="user123")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
    
    def test_refresh_token_longer_expiry(self):
        """Refresh token should have longer default expiry than access token."""
        access_token, _ = create_access_token(subject="user123")
        refresh_token, _ = create_refresh_token(subject="user123")
        
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        
        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    """Tests for token decoding."""
    
    def test_decode_valid_token(self):
        """Valid token should be decoded successfully."""
        token, _ = create_access_token(subject="user123")
        payload = decode_token(token)
        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_invalid_token(self):
        """Invalid token should return None."""
        payload = decode_token("invalid.token.here")
        assert payload is None
    
    def test_decode_malformed_token(self):
        """Malformed token should return None."""
        payload = decode_token("not-a-jwt")
        assert payload is None
    
    def test_decode_empty_token(self):
        """Empty token should return None."""
        payload = decode_token("")
        assert payload is None
    
    def test_decode_token_wrong_secret(self):
        """Token signed with different secret should fail."""
        from jose import jwt
        fake_token = jwt.encode(
            {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm=ALGORITHM
        )
        payload = decode_token(fake_token)
        assert payload is None


class TestVerifyToken:
    """Tests for token verification."""
    
    def test_verify_valid_access_token(self):
        """Valid access token should return subject."""
        subject = "user123"
        token, _ = create_access_token(subject=subject)
        result = verify_token(token, token_type="access")
        assert result == subject
    
    def test_verify_valid_refresh_token(self):
        """Valid refresh token should return subject."""
        subject = "user123"
        token, _ = create_refresh_token(subject=subject)
        result = verify_token(token, token_type="refresh")
        assert result == subject
    
    def test_verify_wrong_token_type(self):
        """Token with wrong type should fail verification."""
        token, _ = create_access_token(subject="user123")
        result = verify_token(token, token_type="refresh")
        assert result is None
    
    def test_verify_expired_token(self):
        """Expired token should fail verification."""
        token, _ = create_access_token(
            subject="user123",
            expires_delta=timedelta(seconds=-10)  # Already expired
        )
        result = verify_token(token, token_type="access")
        assert result is None
    
    def test_verify_invalid_token(self):
        """Invalid token should fail verification."""
        result = verify_token("invalid-token", token_type="access")
        assert result is None


class TestTokenIntegration:
    """Integration tests for token workflow."""
    
    def test_full_token_lifecycle(self):
        """Test complete token create/decode/verify cycle."""
        user_id = "12345"
        
        # Create tokens
        access_token, access_jti = create_access_token(subject=user_id)
        refresh_token, refresh_jti = create_refresh_token(subject=user_id)
        
        # Verify access token
        assert verify_token(access_token, "access") == user_id
        
        # Verify refresh token
        assert verify_token(refresh_token, "refresh") == user_id
        
        # Decode and check JTIs
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        
        assert access_payload["jti"] == access_jti
        assert refresh_payload["jti"] == refresh_jti
        assert access_jti != refresh_jti
    
    def test_token_for_different_users(self):
        """Tokens for different users should have different subjects."""
        token1, _ = create_access_token(subject="user1")
        token2, _ = create_access_token(subject="user2")
        
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        
        assert payload1["sub"] != payload2["sub"]
        assert payload1["jti"] != payload2["jti"]
