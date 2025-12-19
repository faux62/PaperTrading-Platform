"""
PaperTrading Platform - Redis Client
"""
import redis.asyncio as redis
from loguru import logger

from app.config import settings


class RedisClient:
    """Async Redis client wrapper."""
    
    def __init__(self):
        self._client: redis.Redis | None = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            redis_url = settings.redis_url
            self._client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"✅ Redis connected: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client
    
    # =========================
    # Quote Cache Methods
    # =========================
    async def set_quote(self, symbol: str, data: dict, ttl: int = 1800):
        """Cache quote data with TTL (default 30 minutes)."""
        import json
        key = f"quote:{symbol.upper()}"
        await self._client.setex(key, ttl, json.dumps(data))
    
    async def get_quote(self, symbol: str) -> dict | None:
        """Get cached quote data."""
        import json
        key = f"quote:{symbol.upper()}"
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def get_quotes(self, symbols: list[str]) -> dict:
        """Get multiple cached quotes."""
        import json
        keys = [f"quote:{s.upper()}" for s in symbols]
        values = await self._client.mget(keys)
        return {
            symbols[i]: json.loads(v) if v else None 
            for i, v in enumerate(values)
        }
    
    # =========================
    # Rate Limit Methods
    # =========================
    async def increment_rate_limit(self, provider: str) -> int:
        """Increment daily rate limit counter for provider."""
        from datetime import date
        key = f"ratelimit:{provider}:{date.today().isoformat()}"
        count = await self._client.incr(key)
        # Set expiry to end of day + 1 hour buffer
        await self._client.expire(key, 90000)  # 25 hours
        return count
    
    async def get_rate_limit_count(self, provider: str) -> int:
        """Get current rate limit count for provider."""
        from datetime import date
        key = f"ratelimit:{provider}:{date.today().isoformat()}"
        count = await self._client.get(key)
        return int(count) if count else 0
    
    # =========================
    # Provider Health Methods
    # =========================
    async def set_provider_health(self, provider: str, status: str, ttl: int = 60):
        """Set provider health status."""
        key = f"health:{provider}"
        await self._client.setex(key, ttl, status)
    
    async def get_provider_health(self, provider: str) -> str | None:
        """Get provider health status."""
        key = f"health:{provider}"
        return await self._client.get(key)
    
    # =========================
    # Generic Get/Set Methods
    # =========================
    async def get(self, key: str) -> str | None:
        """Get value by key."""
        if not self._client:
            return None
        return await self._client.get(key)
    
    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set value with optional expiry (in seconds)."""
        if not self._client:
            return False
        if ex:
            await self._client.setex(key, ex, value)
        else:
            await self._client.set(key, value)
        return True
    
    # =========================
    # Pub/Sub Methods
    # =========================
    async def publish(self, channel: str, message: str):
        """Publish message to channel."""
        await self._client.publish(channel, message)
    
    def pubsub(self):
        """Get pubsub object for subscribing."""
        return self._client.pubsub()

    # =========================
    # Session Management Methods
    # =========================
    async def create_session(
        self, 
        user_id: int, 
        session_id: str, 
        data: dict,
        ttl: int = 604800  # 7 days default
    ) -> bool:
        """
        Create a new user session.
        
        Args:
            user_id: The user's ID
            session_id: Unique session identifier (e.g., JWT jti)
            data: Session data (device info, IP, etc.)
            ttl: Time to live in seconds (default 7 days)
        
        Returns:
            True if session created successfully
        """
        import json
        key = f"session:{user_id}:{session_id}"
        data["created_at"] = __import__("datetime").datetime.now().isoformat()
        await self._client.setex(key, ttl, json.dumps(data))
        
        # Add to user's session set for tracking all active sessions
        user_sessions_key = f"user_sessions:{user_id}"
        await self._client.sadd(user_sessions_key, session_id)
        await self._client.expire(user_sessions_key, ttl)
        
        return True
    
    async def get_session(self, user_id: int, session_id: str) -> dict | None:
        """
        Get session data.
        
        Args:
            user_id: The user's ID
            session_id: The session identifier
            
        Returns:
            Session data dict or None if not found/expired
        """
        import json
        key = f"session:{user_id}:{session_id}"
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def get_user_sessions(self, user_id: int) -> list[str]:
        """
        Get all active session IDs for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of active session IDs
        """
        key = f"user_sessions:{user_id}"
        sessions = await self._client.smembers(key)
        return list(sessions) if sessions else []
    
    async def delete_session(self, user_id: int, session_id: str) -> bool:
        """
        Delete a specific session (logout from one device).
        
        Args:
            user_id: The user's ID
            session_id: The session identifier
            
        Returns:
            True if session was deleted
        """
        key = f"session:{user_id}:{session_id}"
        user_sessions_key = f"user_sessions:{user_id}"
        
        deleted = await self._client.delete(key)
        await self._client.srem(user_sessions_key, session_id)
        
        return deleted > 0
    
    async def delete_all_user_sessions(self, user_id: int) -> int:
        """
        Delete all sessions for a user (logout from all devices).
        
        Args:
            user_id: The user's ID
            
        Returns:
            Number of sessions deleted
        """
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self._client.smembers(user_sessions_key)
        
        if not session_ids:
            return 0
        
        # Delete all session keys
        keys_to_delete = [f"session:{user_id}:{sid}" for sid in session_ids]
        keys_to_delete.append(user_sessions_key)
        
        deleted = await self._client.delete(*keys_to_delete)
        return deleted
    
    # =========================
    # Token Blacklist Methods
    # =========================
    async def blacklist_token(
        self, 
        token_jti: str, 
        user_id: int,
        ttl: int | None = None
    ) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token_jti: The JWT ID (jti claim)
            user_id: The user's ID (for tracking)
            ttl: Time to live - should match token expiry time
            
        Returns:
            True if token was blacklisted
        """
        import json
        key = f"blacklist:{token_jti}"
        data = {
            "user_id": user_id,
            "blacklisted_at": __import__("datetime").datetime.now().isoformat()
        }
        
        if ttl:
            await self._client.setex(key, ttl, json.dumps(data))
        else:
            # Default to 7 days if no TTL provided
            await self._client.setex(key, 604800, json.dumps(data))
        
        return True
    
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token_jti: The JWT ID (jti claim)
            
        Returns:
            True if token is blacklisted
        """
        key = f"blacklist:{token_jti}"
        return await self._client.exists(key) > 0
    
    async def blacklist_all_user_tokens(self, user_id: int) -> int:
        """
        Blacklist all tokens for a user by deleting all their sessions.
        This effectively invalidates all tokens since we check session validity.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Number of sessions invalidated
        """
        return await self.delete_all_user_sessions(user_id)
    
    # =========================
    # Refresh Token Storage
    # =========================
    async def store_refresh_token(
        self,
        user_id: int,
        token_jti: str,
        ttl: int = 604800  # 7 days
    ) -> bool:
        """
        Store a refresh token reference.
        
        Args:
            user_id: The user's ID
            token_jti: The refresh token's JTI
            ttl: Time to live in seconds
            
        Returns:
            True if stored successfully
        """
        import json
        key = f"refresh_token:{token_jti}"
        data = {
            "user_id": user_id,
            "created_at": __import__("datetime").datetime.now().isoformat()
        }
        await self._client.setex(key, ttl, json.dumps(data))
        
        # Track in user's refresh tokens set
        user_tokens_key = f"user_refresh_tokens:{user_id}"
        await self._client.sadd(user_tokens_key, token_jti)
        await self._client.expire(user_tokens_key, ttl)
        
        return True
    
    async def validate_refresh_token(self, token_jti: str) -> dict | None:
        """
        Validate a refresh token exists and is not revoked.
        
        Args:
            token_jti: The refresh token's JTI
            
        Returns:
            Token data if valid, None otherwise
        """
        import json
        key = f"refresh_token:{token_jti}"
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def revoke_refresh_token(self, token_jti: str, user_id: int) -> bool:
        """
        Revoke a specific refresh token.
        
        Args:
            token_jti: The refresh token's JTI
            user_id: The user's ID
            
        Returns:
            True if token was revoked
        """
        key = f"refresh_token:{token_jti}"
        user_tokens_key = f"user_refresh_tokens:{user_id}"
        
        deleted = await self._client.delete(key)
        await self._client.srem(user_tokens_key, token_jti)
        
        return deleted > 0
    
    async def revoke_all_refresh_tokens(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Number of tokens revoked
        """
        user_tokens_key = f"user_refresh_tokens:{user_id}"
        token_jtis = await self._client.smembers(user_tokens_key)
        
        if not token_jtis:
            return 0
        
        # Delete all refresh token keys
        keys_to_delete = [f"refresh_token:{jti}" for jti in token_jtis]
        keys_to_delete.append(user_tokens_key)
        
        deleted = await self._client.delete(*keys_to_delete)
        return deleted
    
    # =========================
    # User Activity Tracking
    # =========================
    async def update_user_activity(self, user_id: int, activity: str = "api_call"):
        """
        Track user's last activity timestamp.
        
        Args:
            user_id: The user's ID
            activity: Type of activity
        """
        import json
        key = f"user_activity:{user_id}"
        data = {
            "last_activity": __import__("datetime").datetime.now().isoformat(),
            "activity_type": activity
        }
        await self._client.setex(key, 86400, json.dumps(data))  # 24 hours
    
    async def get_user_activity(self, user_id: int) -> dict | None:
        """
        Get user's last activity.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Activity data or None
        """
        import json
        key = f"user_activity:{user_id}"
        data = await self._client.get(key)
        return json.loads(data) if data else None


# Global Redis client instance
redis_client = RedisClient()
