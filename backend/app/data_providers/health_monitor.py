"""
Provider Health Monitor

Monitors the health status of all data providers.
Tracks latency, error rates, and availability.
Implements circuit breaker pattern for automatic failover.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Awaitable
from collections import defaultdict, deque
from loguru import logger


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class HealthConfig:
    """Health monitoring configuration for a provider."""
    # Circuit breaker settings
    failure_threshold: int = 5        # Failures before opening circuit
    success_threshold: int = 3        # Successes in half-open to close
    timeout_seconds: float = 60.0     # Time before trying half-open
    
    # Health check settings
    health_check_interval: float = 30.0  # Seconds between health checks
    max_latency_ms: float = 5000.0       # Max acceptable latency
    
    # Degraded mode thresholds
    warning_latency_ms: float = 2000.0   # Latency warning threshold
    warning_error_rate: float = 0.1      # Error rate warning (10%)
    critical_error_rate: float = 0.3     # Error rate critical (30%)


@dataclass
class HealthMetrics:
    """Health metrics for a provider."""
    provider: str
    
    # Latency tracking (last N requests)
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Error tracking
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    # Circuit breaker state
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_opened_at: Optional[datetime] = None
    
    # Timestamps
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    
    # Status
    is_healthy: bool = True
    is_available: bool = True
    status_message: str = "OK"
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)
    
    @property
    def p95_latency_ms(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class ProviderHealthMonitor:
    """
    Monitors health status of data providers.
    
    Features:
    - Latency tracking with percentiles
    - Error rate monitoring
    - Circuit breaker pattern
    - Automatic health checks
    - Event callbacks for status changes
    """
    
    def __init__(self):
        self._configs: dict[str, HealthConfig] = {}
        self._metrics: dict[str, HealthMetrics] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._health_check_tasks: dict[str, asyncio.Task] = {}
        self._status_callbacks: list[Callable[[str, bool, str], Awaitable[None]]] = []
        
    def configure(self, provider: str, config: Optional[HealthConfig] = None) -> None:
        """Configure health monitoring for a provider."""
        self._configs[provider] = config or HealthConfig()
        if provider not in self._metrics:
            self._metrics[provider] = HealthMetrics(provider=provider)
        logger.info(f"Health monitor configured for {provider}")
    
    def register_status_callback(
        self,
        callback: Callable[[str, bool, str], Awaitable[None]]
    ) -> None:
        """
        Register a callback for status changes.
        
        Callback receives: provider name, is_healthy, status message
        """
        self._status_callbacks.append(callback)
    
    async def record_success(self, provider: str, latency_ms: float) -> None:
        """Record a successful request."""
        async with self._locks[provider]:
            metrics = self._get_or_create_metrics(provider)
            config = self._configs.get(provider, HealthConfig())
            
            # Update counters
            metrics.total_requests += 1
            metrics.successful_requests += 1
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
            metrics.last_success = datetime.utcnow()
            
            # Record latency
            metrics.latencies.append(latency_ms)
            
            # Handle circuit breaker state
            if metrics.circuit_state == CircuitState.HALF_OPEN:
                if metrics.consecutive_successes >= config.success_threshold:
                    await self._close_circuit(provider, metrics)
            
            # Check if we should warn about latency
            if latency_ms > config.warning_latency_ms:
                logger.warning(
                    f"High latency for {provider}: {latency_ms:.0f}ms"
                )
            
            # Update overall health status
            await self._update_health_status(provider, metrics, config)
    
    async def record_failure(self, provider: str, error: Optional[str] = None) -> None:
        """Record a failed request."""
        async with self._locks[provider]:
            metrics = self._get_or_create_metrics(provider)
            config = self._configs.get(provider, HealthConfig())
            
            # Update counters
            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0
            metrics.last_failure = datetime.utcnow()
            
            logger.warning(f"Request failed for {provider}: {error}")
            
            # Check if we should open circuit
            if metrics.circuit_state == CircuitState.CLOSED:
                if metrics.consecutive_failures >= config.failure_threshold:
                    await self._open_circuit(provider, metrics)
            elif metrics.circuit_state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                await self._open_circuit(provider, metrics)
            
            # Update overall health status
            await self._update_health_status(provider, metrics, config)
    
    def can_request(self, provider: str) -> bool:
        """
        Check if a request can be made to the provider.
        
        Returns False if circuit is open, True otherwise.
        """
        metrics = self._metrics.get(provider)
        if not metrics:
            return True
        
        config = self._configs.get(provider, HealthConfig())
        
        if metrics.circuit_state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if metrics.circuit_opened_at:
                elapsed = (datetime.utcnow() - metrics.circuit_opened_at).total_seconds()
                if elapsed >= config.timeout_seconds:
                    metrics.circuit_state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit for {provider} transitioning to half-open")
                    return True
            return False
        
        return True
    
    async def _open_circuit(self, provider: str, metrics: HealthMetrics) -> None:
        """Open the circuit breaker."""
        metrics.circuit_state = CircuitState.OPEN
        metrics.circuit_opened_at = datetime.utcnow()
        metrics.is_available = False
        metrics.status_message = "Circuit breaker OPEN - too many failures"
        
        logger.error(f"Circuit breaker OPENED for {provider}")
        await self._notify_status_change(provider, False, metrics.status_message)
    
    async def _close_circuit(self, provider: str, metrics: HealthMetrics) -> None:
        """Close the circuit breaker (return to normal)."""
        metrics.circuit_state = CircuitState.CLOSED
        metrics.circuit_opened_at = None
        metrics.is_available = True
        metrics.consecutive_failures = 0
        metrics.status_message = "OK"
        
        logger.info(f"Circuit breaker CLOSED for {provider} - recovered")
        await self._notify_status_change(provider, True, "Recovered")
    
    async def _update_health_status(
        self,
        provider: str,
        metrics: HealthMetrics,
        config: HealthConfig,
    ) -> None:
        """Update overall health status based on metrics."""
        was_healthy = metrics.is_healthy
        
        # Check various health indicators
        issues = []
        
        # Error rate check
        if metrics.error_rate >= config.critical_error_rate:
            issues.append(f"Critical error rate: {metrics.error_rate*100:.1f}%")
            metrics.is_healthy = False
        elif metrics.error_rate >= config.warning_error_rate:
            issues.append(f"High error rate: {metrics.error_rate*100:.1f}%")
        
        # Latency check
        if metrics.avg_latency_ms > config.max_latency_ms:
            issues.append(f"Excessive latency: {metrics.avg_latency_ms:.0f}ms")
            metrics.is_healthy = False
        elif metrics.avg_latency_ms > config.warning_latency_ms:
            issues.append(f"High latency: {metrics.avg_latency_ms:.0f}ms")
        
        # Circuit breaker check
        if metrics.circuit_state == CircuitState.OPEN:
            metrics.is_healthy = False
        
        # Set status message
        if not issues:
            metrics.is_healthy = True
            metrics.status_message = "OK"
        else:
            metrics.status_message = "; ".join(issues)
        
        # Notify if health status changed
        if was_healthy != metrics.is_healthy:
            await self._notify_status_change(
                provider, 
                metrics.is_healthy, 
                metrics.status_message
            )
    
    async def _notify_status_change(
        self, 
        provider: str, 
        is_healthy: bool, 
        message: str
    ) -> None:
        """Notify registered callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                await callback(provider, is_healthy, message)
            except Exception as e:
                logger.error(f"Error in health status callback: {e}")
    
    def _get_or_create_metrics(self, provider: str) -> HealthMetrics:
        """Get or create metrics for a provider."""
        if provider not in self._metrics:
            self._metrics[provider] = HealthMetrics(provider=provider)
        return self._metrics[provider]
    
    def get_health(self, provider: str) -> dict:
        """Get health status for a provider."""
        metrics = self._metrics.get(provider)
        if not metrics:
            return {
                "provider": provider,
                "configured": False,
                "is_healthy": True,
                "is_available": True,
            }
        
        return {
            "provider": provider,
            "configured": True,
            "is_healthy": metrics.is_healthy,
            "is_available": metrics.is_available,
            "circuit_state": metrics.circuit_state.value,
            "status_message": metrics.status_message,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "error_rate": round(metrics.error_rate * 100, 2),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p95_latency_ms": round(metrics.p95_latency_ms, 2),
                "consecutive_failures": metrics.consecutive_failures,
            },
            "timestamps": {
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
            },
        }
    
    def get_all_health(self) -> dict[str, dict]:
        """Get health status for all providers."""
        return {
            provider: self.get_health(provider)
            for provider in self._metrics.keys()
        }
    
    def get_healthy_providers(self) -> list[str]:
        """Get list of healthy and available providers."""
        return [
            provider
            for provider, metrics in self._metrics.items()
            if metrics.is_healthy and metrics.is_available
        ]
    
    def reset_metrics(self, provider: str) -> None:
        """Reset metrics for a provider."""
        if provider in self._metrics:
            self._metrics[provider] = HealthMetrics(provider=provider)
            logger.info(f"Health metrics reset for {provider}")


# Global health monitor instance
health_monitor = ProviderHealthMonitor()
