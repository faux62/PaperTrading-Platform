"""
Startup Task Orchestrator

Manages startup tasks to avoid overloading the system and hitting rate limits.

Strategies:
1. Sequential execution of heavy tasks (not parallel)
2. Staggered delays between task phases
3. Market-hours awareness (skip some tasks if markets are closed)
4. Priority-based execution (critical tasks first)
"""
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Awaitable, Optional, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

from app.scheduler.market_hours import is_us_market_open, is_eu_market_open, is_asia_market_open


class TaskPriority(Enum):
    """Task execution priority."""
    CRITICAL = 1    # Must run immediately (e.g., FX rates for portfolio values)
    HIGH = 2        # Should run soon (e.g., EOD data if stale)
    NORMAL = 3      # Can wait (e.g., quote updates)
    LOW = 4         # Run only if system is idle


@dataclass
class StartupTask:
    """Definition of a startup task."""
    name: str
    func: Callable[[], Awaitable[Any]]
    priority: TaskPriority = TaskPriority.NORMAL
    skip_if_markets_closed: bool = False
    max_duration_seconds: int = 300  # 5 min timeout
    delay_after_seconds: int = 10    # Delay before next task
    
    # Runtime state
    completed: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StartupOrchestrator:
    """
    Orchestrates startup tasks to avoid overloading the system.
    
    Usage:
        orchestrator = StartupOrchestrator()
        
        orchestrator.register_task(
            name="fx_rates",
            func=update_fx_rates,
            priority=TaskPriority.CRITICAL
        )
        
        orchestrator.register_task(
            name="eod_data", 
            func=update_eod_data,
            priority=TaskPriority.HIGH,
            delay_after_seconds=30
        )
        
        await orchestrator.run_startup_sequence()
    """
    
    def __init__(self):
        self.tasks: Dict[str, StartupTask] = {}
        self._running = False
        self._current_task: Optional[str] = None
    
    def register_task(
        self,
        name: str,
        func: Callable[[], Awaitable[Any]],
        priority: TaskPriority = TaskPriority.NORMAL,
        skip_if_markets_closed: bool = False,
        max_duration_seconds: int = 300,
        delay_after_seconds: int = 10
    ) -> None:
        """Register a startup task."""
        self.tasks[name] = StartupTask(
            name=name,
            func=func,
            priority=priority,
            skip_if_markets_closed=skip_if_markets_closed,
            max_duration_seconds=max_duration_seconds,
            delay_after_seconds=delay_after_seconds
        )
        logger.debug(f"Registered startup task: {name} (priority={priority.name})")
    
    def _should_skip_task(self, task: StartupTask) -> tuple[bool, str]:
        """Check if a task should be skipped based on market hours."""
        if not task.skip_if_markets_closed:
            return False, ""
        
        # Check if any market is open
        any_market_open = (
            is_us_market_open() or 
            is_eu_market_open() or 
            is_asia_market_open()
        )
        
        if not any_market_open:
            return True, "all markets closed"
        
        return False, ""
    
    async def run_startup_sequence(self) -> Dict[str, Any]:
        """
        Run all startup tasks in priority order.
        
        Returns:
            Summary of task execution results
        """
        if self._running:
            logger.warning("Startup sequence already running")
            return {"error": "already_running"}
        
        self._running = True
        logger.info(f"Starting startup sequence with {len(self.tasks)} tasks")
        
        # Sort tasks by priority
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.priority.value
        )
        
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "tasks": {}
        }
        
        for task in sorted_tasks:
            self._current_task = task.name
            
            # Check if we should skip
            should_skip, reason = self._should_skip_task(task)
            if should_skip:
                logger.info(f"Skipping task '{task.name}': {reason}")
                results["tasks"][task.name] = {"skipped": True, "reason": reason}
                continue
            
            # Execute task with timeout
            logger.info(f"Executing startup task: {task.name} (priority={task.priority.name})")
            task.started_at = datetime.utcnow()
            
            try:
                task.result = await asyncio.wait_for(
                    task.func(),
                    timeout=task.max_duration_seconds
                )
                task.completed = True
                task.completed_at = datetime.utcnow()
                
                duration = (task.completed_at - task.started_at).total_seconds()
                logger.info(f"Task '{task.name}' completed in {duration:.1f}s")
                
                results["tasks"][task.name] = {
                    "success": True,
                    "duration_seconds": duration,
                    "result": _summarize_result(task.result)
                }
                
            except asyncio.TimeoutError:
                task.error = f"Timeout after {task.max_duration_seconds}s"
                logger.error(f"Task '{task.name}' timed out")
                results["tasks"][task.name] = {"success": False, "error": task.error}
                
            except Exception as e:
                task.error = str(e)
                logger.error(f"Task '{task.name}' failed: {e}")
                results["tasks"][task.name] = {"success": False, "error": task.error}
            
            # Delay before next task (if not the last one)
            if task != sorted_tasks[-1] and task.delay_after_seconds > 0:
                logger.debug(f"Waiting {task.delay_after_seconds}s before next task")
                await asyncio.sleep(task.delay_after_seconds)
        
        self._running = False
        self._current_task = None
        
        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Startup sequence completed: {len(results['tasks'])} tasks processed")
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the orchestrator."""
        return {
            "running": self._running,
            "current_task": self._current_task,
            "tasks": {
                name: {
                    "priority": task.priority.name,
                    "completed": task.completed,
                    "error": task.error
                }
                for name, task in self.tasks.items()
            }
        }


def _summarize_result(result: Any) -> Any:
    """Summarize a task result for logging (avoid huge outputs)."""
    if result is None:
        return None
    if isinstance(result, dict):
        # Return dict as-is if small, otherwise just keys
        if len(str(result)) < 500:
            return result
        return {"keys": list(result.keys()), "_truncated": True}
    if isinstance(result, (list, tuple)):
        return {"count": len(result), "_truncated": True}
    return str(result)[:200]


# Singleton instance
_startup_orchestrator: Optional[StartupOrchestrator] = None


def get_startup_orchestrator() -> StartupOrchestrator:
    """Get the singleton startup orchestrator instance."""
    global _startup_orchestrator
    if _startup_orchestrator is None:
        _startup_orchestrator = StartupOrchestrator()
    return _startup_orchestrator
