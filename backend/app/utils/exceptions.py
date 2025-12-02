"""
PaperTrading Platform - Custom Exceptions
Application-specific exceptions with HTTP error handling
"""
from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class PaperTradingException(Exception):
    """Base exception for PaperTrading Platform."""
    
    def __init__(
        self,
        message: str = "An error occurred",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


# =========================
# Authentication Exceptions
# =========================

class AuthenticationError(PaperTradingException):
    """Authentication related errors."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, code="INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """Token is invalid."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, code="INVALID_TOKEN")


class InactiveUserError(AuthenticationError):
    """User account is inactive."""
    
    def __init__(self, message: str = "User account is inactive"):
        super().__init__(message=message, code="INACTIVE_USER")


class InsufficientPermissionsError(AuthenticationError):
    """User doesn't have required permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, code="INSUFFICIENT_PERMISSIONS")


# =========================
# User Exceptions
# =========================

class UserError(PaperTradingException):
    """User related errors."""
    pass


class UserNotFoundError(UserError):
    """User not found."""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(message=message, code="USER_NOT_FOUND")


class UserAlreadyExistsError(UserError):
    """User already exists."""
    
    def __init__(self, message: str = "User already exists"):
        super().__init__(message=message, code="USER_EXISTS")


class EmailAlreadyRegisteredError(UserError):
    """Email already registered."""
    
    def __init__(self, message: str = "Email already registered"):
        super().__init__(message=message, code="EMAIL_REGISTERED")


class UsernameAlreadyTakenError(UserError):
    """Username already taken."""
    
    def __init__(self, message: str = "Username already taken"):
        super().__init__(message=message, code="USERNAME_TAKEN")


# =========================
# Portfolio Exceptions
# =========================

class PortfolioError(PaperTradingException):
    """Portfolio related errors."""
    pass


class PortfolioNotFoundError(PortfolioError):
    """Portfolio not found."""
    
    def __init__(self, message: str = "Portfolio not found"):
        super().__init__(message=message, code="PORTFOLIO_NOT_FOUND")


class InsufficientFundsError(PortfolioError):
    """Insufficient funds for operation."""
    
    def __init__(self, message: str = "Insufficient funds"):
        super().__init__(message=message, code="INSUFFICIENT_FUNDS")


class PortfolioLimitExceededError(PortfolioError):
    """Maximum portfolio limit exceeded."""
    
    def __init__(self, message: str = "Portfolio limit exceeded"):
        super().__init__(message=message, code="PORTFOLIO_LIMIT_EXCEEDED")


# =========================
# Trading Exceptions
# =========================

class TradingError(PaperTradingException):
    """Trading related errors."""
    pass


class InvalidOrderError(TradingError):
    """Invalid order parameters."""
    
    def __init__(self, message: str = "Invalid order"):
        super().__init__(message=message, code="INVALID_ORDER")


class MarketClosedError(TradingError):
    """Market is closed."""
    
    def __init__(self, message: str = "Market is closed"):
        super().__init__(message=message, code="MARKET_CLOSED")


class PositionNotFoundError(TradingError):
    """Position not found."""
    
    def __init__(self, message: str = "Position not found"):
        super().__init__(message=message, code="POSITION_NOT_FOUND")


class InsufficientSharesError(TradingError):
    """Insufficient shares to sell."""
    
    def __init__(self, message: str = "Insufficient shares"):
        super().__init__(message=message, code="INSUFFICIENT_SHARES")


# =========================
# Market Data Exceptions
# =========================

class MarketDataError(PaperTradingException):
    """Market data related errors."""
    pass


class SymbolNotFoundError(MarketDataError):
    """Symbol not found."""
    
    def __init__(self, symbol: str = ""):
        message = f"Symbol '{symbol}' not found" if symbol else "Symbol not found"
        super().__init__(message=message, code="SYMBOL_NOT_FOUND")


class DataProviderError(MarketDataError):
    """Data provider error."""
    
    def __init__(self, provider: str = "", message: str = "Provider error"):
        super().__init__(
            message=f"{provider}: {message}" if provider else message,
            code="PROVIDER_ERROR"
        )


class RateLimitExceededError(MarketDataError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED")


# =========================
# Database Exceptions
# =========================

class DatabaseError(PaperTradingException):
    """Database related errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection error."""
    
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message=message, code="DB_CONNECTION_ERROR")


# =========================
# HTTP Exception Helpers
# =========================

def raise_not_found(message: str = "Resource not found"):
    """Raise 404 Not Found exception."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=message
    )


def raise_bad_request(message: str = "Bad request"):
    """Raise 400 Bad Request exception."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def raise_unauthorized(message: str = "Unauthorized"):
    """Raise 401 Unauthorized exception."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"}
    )


def raise_forbidden(message: str = "Forbidden"):
    """Raise 403 Forbidden exception."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def raise_conflict(message: str = "Conflict"):
    """Raise 409 Conflict exception."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message
    )


def raise_internal_error(message: str = "Internal server error"):
    """Raise 500 Internal Server Error exception."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )
