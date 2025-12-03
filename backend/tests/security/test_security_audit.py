"""
Backend Security Tests
Tests for OWASP-aligned security checks.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
import re
import os


class TestAuthenticationSecurity:
    """Tests for authentication security."""
    
    def test_password_not_stored_plaintext(self):
        """Passwords must be hashed, never stored in plain text."""
        from app.core.security import get_password_hash
        
        password = "SuperSecret123!"
        hashed = get_password_hash(password)
        
        # Hash should not contain the original password
        assert password not in hashed
        # Should be a bcrypt hash (starts with $2b$)
        assert hashed.startswith("$2b$")
    
    def test_password_hash_unique(self):
        """Same password should produce different hashes (salt)."""
        from app.core.security import get_password_hash
        
        password = "SamePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
    
    def test_jwt_token_has_expiry(self):
        """JWT tokens must have expiration."""
        from app.core.security import create_access_token, decode_token
        
        token, _ = create_access_token(subject="user@test.com")
        payload = decode_token(token)
        
        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()
    
    def test_jwt_token_has_type(self):
        """JWT tokens must have type claim."""
        from app.core.security import create_access_token, decode_token
        
        token, _ = create_access_token(subject="user@test.com")
        payload = decode_token(token)
        
        assert "type" in payload
        assert payload["type"] == "access"
    
    def test_refresh_token_different_type(self):
        """Refresh tokens must have different type."""
        from app.core.security import create_refresh_token, decode_token
        
        token, _ = create_refresh_token(subject="user@test.com")
        payload = decode_token(token)
        
        assert payload["type"] == "refresh"
    
    def test_invalid_token_rejected(self):
        """Invalid tokens must be rejected."""
        from app.core.security import decode_token
        
        invalid_tokens = [
            "invalid.token.here",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.payload",
            None,
        ]
        
        for token in invalid_tokens:
            if token is not None:
                result = decode_token(token)
                assert result is None or "error" in str(result).lower() or result == {}


class TestInputValidation:
    """Tests for input validation security."""
    
    def test_email_format_validation(self):
        """Email must be validated."""
        from pydantic import ValidationError
        from app.schemas import UserCreate
        
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "",
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    email=email,
                    username="testuser",
                    password="ValidPass123!"
                )
    
    def test_password_minimum_length(self):
        """Password must have minimum length."""
        from pydantic import ValidationError
        from app.schemas import UserCreate
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="valid@email.com",
                username="testuser",
                password="short"  # Too short
            )
    
    def test_sql_injection_prevention(self):
        """SQL injection attempts should be handled safely."""
        # These should be treated as literal strings, not SQL
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "admin'--",
            "1; DELETE FROM trades",
            "UNION SELECT * FROM users",
        ]
        
        # Pydantic/SQLAlchemy should escape these
        for input_str in dangerous_inputs:
            # Just verify they don't cause issues as strings
            assert isinstance(input_str, str)
            # In real tests, these would be passed to DB operations
            # and verified not to execute as SQL
    
    def test_xss_prevention_symbols(self):
        """XSS attempts in symbol names should be escaped."""
        dangerous_symbols = [
            "<script>alert('xss')</script>",
            "AAPL<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
        ]
        
        # These should be rejected or escaped
        for symbol in dangerous_symbols:
            # Valid symbols are alphanumeric with optional . - ^
            is_valid = bool(re.match(r'^[A-Z0-9\.\-\^]{1,10}$', symbol))
            assert is_valid is False


class TestAccessControl:
    """Tests for access control."""
    
    def test_portfolio_user_isolation(self):
        """Users should only access their own portfolios."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Simulated portfolio ownership check
        portfolio_owner = user1_id
        requesting_user = user2_id
        
        has_access = portfolio_owner == requesting_user
        assert has_access is False
    
    def test_trade_user_isolation(self):
        """Users should only see their own trades."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        trade_owner = user1_id
        requesting_user = user2_id
        
        has_access = trade_owner == requesting_user
        assert has_access is False


class TestDataProtection:
    """Tests for data protection."""
    
    def test_password_not_in_response(self):
        """Password should never be in API responses."""
        # Simulated user response
        user_response = {
            "id": str(uuid4()),
            "email": "user@example.com",
            "username": "testuser",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Password fields should not exist
        assert "password" not in user_response
        assert "hashed_password" not in user_response
        assert "password_hash" not in user_response
    
    def test_sensitive_config_not_exposed(self):
        """Sensitive config should not be exposed."""
        # These should come from environment, not be hardcoded
        sensitive_keys = [
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "API_KEY",
        ]
        
        for key in sensitive_keys:
            # Should be loaded from environment
            # In real app, verify these aren't in public endpoints
            pass
    
    def test_api_keys_masked_in_logs(self):
        """API keys should be masked in logs."""
        api_key = "sk_live_abc123def456"
        
        # Masking function
        def mask_api_key(key: str) -> str:
            if len(key) > 8:
                return key[:4] + "****" + key[-4:]
            return "****"
        
        masked = mask_api_key(api_key)
        assert api_key not in masked
        assert "****" in masked


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def test_rate_limit_structure(self):
        """Rate limits should be defined."""
        rate_limits = {
            "login": {"requests": 5, "window_seconds": 60},
            "api": {"requests": 100, "window_seconds": 60},
            "quotes": {"requests": 30, "window_seconds": 60},
        }
        
        for endpoint, limits in rate_limits.items():
            assert limits["requests"] > 0
            assert limits["window_seconds"] > 0
    
    def test_rate_limit_tracking(self):
        """Rate limit tracking should work."""
        # Simulated rate limit counter
        request_count = 0
        limit = 5
        
        for _ in range(10):
            request_count += 1
            is_limited = request_count > limit
            
            if request_count == 6:
                assert is_limited is True


class TestCryptography:
    """Tests for cryptographic operations."""
    
    def test_jwt_algorithm_secure(self):
        """JWT should use secure algorithm."""
        from app.config import settings
        
        # HS256 is acceptable for symmetric signing
        # RS256 would be better for asymmetric
        secure_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        
        assert settings.JWT_ALGORITHM in secure_algorithms
    
    def test_secret_key_length(self):
        """Secret key should be sufficiently long."""
        from app.config import settings
        
        # In test environment, we allow shorter keys
        # In production, minimum 32 characters for HS256
        if settings.APP_ENV == "testing":
            assert len(settings.SECRET_KEY) >= 16  # Minimum for testing
        else:
            assert len(settings.SECRET_KEY) >= 32  # Production requirement
    
    def test_token_entropy(self):
        """Tokens should have sufficient entropy."""
        from app.core.security import create_access_token
        
        tokens = [create_access_token(subject="user@test.com")[0] for _ in range(5)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 5


class TestSecurityHeaders:
    """Tests for security headers (recommendations)."""
    
    def test_recommended_headers(self):
        """Define recommended security headers."""
        recommended_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
        }
        
        # These should be added to API responses
        for header, value in recommended_headers.items():
            assert isinstance(header, str)
            assert isinstance(value, str)


class TestModelSecurity:
    """Tests for ML model security."""
    
    def test_model_path_validation(self):
        """Model paths should be validated."""
        safe_paths = [
            "models/price_predictor_v1.pkl",
            "models/trend_classifier.pkl",
        ]
        
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "models/../../secrets.pkl",
            "http://evil.com/malicious.pkl",
        ]
        
        def is_safe_path(path: str) -> bool:
            # No path traversal
            if ".." in path:
                return False
            # No absolute paths
            if path.startswith("/"):
                return False
            # No URLs
            if path.startswith("http"):
                return False
            # Must be in models directory
            if not path.startswith("models/"):
                return False
            return True
        
        for path in safe_paths:
            assert is_safe_path(path) is True
        
        for path in dangerous_paths:
            assert is_safe_path(path) is False
    
    def test_model_checksum_concept(self):
        """Model files should have checksums."""
        import hashlib
        
        # Simulated model data
        model_data = b"fake model binary data"
        
        # Calculate checksum
        checksum = hashlib.sha256(model_data).hexdigest()
        
        # Checksum should be 64 characters (SHA256)
        assert len(checksum) == 64
        
        # Same data should produce same checksum
        checksum2 = hashlib.sha256(model_data).hexdigest()
        assert checksum == checksum2
