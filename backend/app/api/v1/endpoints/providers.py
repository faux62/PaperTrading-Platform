"""
PaperTrading Platform - Provider Status Endpoints
Monitor rate limits, budget, and health status of data providers
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
from loguru import logger

from app.dependencies import get_current_active_user
from app.db.models.user import User
from app.data_providers import (
    rate_limiter,
    budget_tracker,
    health_monitor,
    orchestrator,
    failover_manager,
)

router = APIRouter()


@router.get(
    "/status",
    summary="Get all providers status",
    description="Get status of all registered data providers including rate limits, budget, and health."
)
async def get_providers_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive status of all providers."""
    providers_status = {}
    
    # Get all registered providers
    for name in failover_manager._providers.keys():
        # Get rate limit stats
        rate_stats = rate_limiter.get_stats(name)
        
        # Get health metrics
        health_metrics = health_monitor._metrics.get(name)
        health_data = {}
        if health_metrics:
            health_data = {
                "is_healthy": health_metrics.is_healthy,
                "circuit_state": health_metrics.circuit_state.value,
                "avg_latency_ms": round(health_metrics.avg_latency_ms, 2),
                "error_rate": round(health_metrics.error_rate * 100, 2),
            }
        
        # Get budget info
        budget_config = budget_tracker._configs.get(name)
        budget_usage = budget_tracker._usage.get(name)
        budget_data = {}
        if budget_config:
            budget_data = {
                "daily_limit": float(budget_config.daily_limit) if budget_config.daily_limit else None,
                "daily_spent": float(budget_usage.daily_spent) if budget_usage else 0,
            }
        
        providers_status[name] = {
            "rate_limit": rate_stats,
            "budget": budget_data,
            "health": health_data,
        }
    
    return {
        "providers": providers_status,
        "total_providers": len(providers_status),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/rate-limits",
    summary="Get rate limit status",
    description="Get rate limit status for all providers."
)
async def get_rate_limits(
    current_user: User = Depends(get_current_active_user)
):
    """Get rate limit status for all providers."""
    rate_limits = {}
    
    for name in failover_manager._providers.keys():
        stats = rate_limiter.get_stats(name)
        if stats.get("configured"):
            rate_limits[name] = {
                "limits": stats.get("limits", {}),
                "remaining": stats.get("remaining", {}),
                "can_proceed": stats.get("can_proceed", True),
                "wait_time_seconds": stats.get("wait_time", 0),
                "usage_percent": _calculate_usage_percent(stats),
            }
    
    return {
        "rate_limits": rate_limits,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/rate-limits/{provider}",
    summary="Get rate limit for specific provider",
    description="Get detailed rate limit status for a specific provider."
)
async def get_provider_rate_limit(
    provider: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get rate limit status for a specific provider."""
    stats = rate_limiter.get_stats(provider)
    
    if not stats.get("configured"):
        raise HTTPException(status_code=404, detail=f"Provider {provider} not configured")
    
    return {
        "provider": provider,
        "limits": stats.get("limits", {}),
        "remaining": stats.get("remaining", {}),
        "can_proceed": stats.get("can_proceed", True),
        "wait_time_seconds": stats.get("wait_time", 0),
        "usage_percent": _calculate_usage_percent(stats),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/health",
    summary="Get health status of all providers",
    description="Get health metrics including latency, error rates, and circuit breaker status."
)
async def get_providers_health(
    current_user: User = Depends(get_current_active_user)
):
    """Get health status for all providers."""
    health_status = {}
    
    for name in failover_manager._providers.keys():
        metrics = health_monitor._metrics.get(name)
        if metrics:
            health_status[name] = {
                "is_healthy": metrics.is_healthy,
                "is_available": metrics.is_available,
                "circuit_state": metrics.circuit_state.value,
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p95_latency_ms": round(metrics.p95_latency_ms, 2),
                "error_rate": round(metrics.error_rate * 100, 2),
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
                "status_message": metrics.status_message,
            }
    
    # Calculate summary
    healthy_count = sum(1 for s in health_status.values() if s.get("is_healthy"))
    
    return {
        "providers": health_status,
        "summary": {
            "total": len(health_status),
            "healthy": healthy_count,
            "unhealthy": len(health_status) - healthy_count,
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/budget",
    summary="Get budget usage for all providers",
    description="Get budget consumption and remaining allocation for all providers."
)
async def get_budget_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get budget status for all providers."""
    budget_status = {}
    
    for name in failover_manager._providers.keys():
        usage = budget_tracker._usage.get(name)
        config = budget_tracker._configs.get(name)
        
        if config:
            daily_remaining = None
            monthly_remaining = None
            daily_usage_percent = 0
            monthly_usage_percent = 0
            
            if config.daily_limit > 0:
                daily_remaining = float(config.daily_limit - (usage.daily_spent if usage else 0))
                if usage:
                    daily_usage_percent = round((float(usage.daily_spent) / float(config.daily_limit)) * 100, 2)
            
            if config.monthly_limit > 0:
                monthly_remaining = float(config.monthly_limit - (usage.monthly_spent if usage else 0))
                if usage:
                    monthly_usage_percent = round((float(usage.monthly_spent) / float(config.monthly_limit)) * 100, 2)
            
            budget_status[name] = {
                "daily_limit": float(config.daily_limit) if config.daily_limit else None,
                "daily_spent": float(usage.daily_spent) if usage else 0,
                "daily_remaining": daily_remaining,
                "daily_usage_percent": daily_usage_percent,
                "monthly_limit": float(config.monthly_limit) if config.monthly_limit else None,
                "monthly_spent": float(usage.monthly_spent) if usage else 0,
                "monthly_remaining": monthly_remaining,
                "monthly_usage_percent": monthly_usage_percent,
                "request_count": usage.request_count if usage else 0,
                "cost_per_request": float(config.cost_per_request),
            }
        else:
            # No budget configured
            budget_status[name] = {
                "daily_limit": None,
                "daily_spent": 0,
                "daily_remaining": None,
                "daily_usage_percent": 0,
                "monthly_limit": None,
                "monthly_spent": 0,
                "monthly_remaining": None,
                "monthly_usage_percent": 0,
                "request_count": 0,
                "cost_per_request": 0,
                "status": "no_budget_configured"
            }
    
    return {
        "budgets": budget_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post(
    "/reset-daily/{provider}",
    summary="Reset daily counters for a provider",
    description="Reset daily rate limit and budget counters for a specific provider."
)
async def reset_daily_counters(
    provider: str,
    current_user: User = Depends(get_current_active_user)
):
    """Reset daily counters for a provider (admin action)."""
    if provider not in failover_manager._providers:
        raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
    
    rate_limiter.reset_daily(provider)
    
    # Reset budget daily
    usage = budget_tracker._usage.get(provider)
    if usage:
        usage.reset_daily()
    
    logger.info(f"Daily counters reset for {provider} by user {current_user.id}")
    
    return {
        "message": f"Daily counters reset for {provider}",
        "provider": provider,
        "timestamp": datetime.utcnow().isoformat()
    }


def _calculate_usage_percent(stats: dict) -> dict:
    """Calculate usage percentage for each rate limit window."""
    usage = {}
    limits = stats.get("limits", {})
    remaining = stats.get("remaining", {})
    
    for window in ["per_minute", "per_hour", "per_day"]:
        limit = limits.get(window)
        remain = remaining.get(window)
        if limit and remain is not None:
            used = limit - remain
            usage[window] = round((used / limit) * 100, 2)
    
    return usage
