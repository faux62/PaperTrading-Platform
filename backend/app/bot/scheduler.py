"""
Trading Assistant Bot - Core Scheduler

Manages all scheduled bot tasks including:
- Pre-market analysis
- Real-time monitoring
- Post-market reports
- Position tracking
"""
from datetime import datetime, timedelta, time
from typing import Optional, Callable, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from loguru import logger
import asyncio

from app.scheduler.market_hours import (
    MarketHoursManager,
    MarketSession,
    get_market_hours_manager,
    is_us_market_open,
)


class BotScheduler:
    """
    Trading Assistant Bot Scheduler.
    
    Manages scheduled tasks aligned with market hours:
    - Pre-market: 06:00-09:30 ET
    - Market hours: 09:30-16:00 ET  
    - Post-market: 16:00-18:00 ET
    """
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.market_hours = get_market_hours_manager()
        self._is_running = False
        self._registered_jobs: dict[str, dict] = {}
        
    def initialize(self) -> None:
        """Initialize the scheduler with job stores and executors."""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple missed runs into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 60 * 5  # 5 minutes grace for missed jobs
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/New_York'  # All times in ET for US market focus
        )
        
        logger.info("Bot scheduler initialized")
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler:
            self.initialize()
        
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Bot scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler and self._is_running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Bot scheduler stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
    
    # ==================== Job Registration ====================
    
    def add_pre_market_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = 6,
        minute: int = 0,
        **kwargs
    ) -> None:
        """
        Add a job that runs during pre-market hours (default 6:00 AM ET).
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            hour: Hour to run (ET timezone)
            minute: Minute to run
            **kwargs: Additional arguments for the job
        """
        if not self.scheduler:
            self.initialize()
        
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week='mon-fri',
            timezone='America/New_York'
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=f"PreMarket: {job_id}",
            replace_existing=True,
            **kwargs
        )
        
        self._registered_jobs[job_id] = {
            'type': 'pre_market',
            'schedule': f'{hour:02d}:{minute:02d} ET Mon-Fri'
        }
        logger.info(f"Registered pre-market job: {job_id} at {hour:02d}:{minute:02d} ET")
    
    def add_market_hours_job(
        self,
        job_id: str,
        func: Callable,
        interval_minutes: int = 5,
        **kwargs
    ) -> None:
        """
        Add a job that runs during market hours at specified interval.
        
        The job will only execute if US market is open.
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            interval_minutes: Minutes between executions
            **kwargs: Additional arguments for the job
        """
        if not self.scheduler:
            self.initialize()
        
        async def market_hours_wrapper():
            """Wrapper that checks market hours before executing."""
            if await is_us_market_open():
                await func()
            else:
                logger.debug(f"Skipping {job_id} - market closed")
        
        trigger = IntervalTrigger(
            minutes=interval_minutes,
            start_date=datetime.now().replace(hour=9, minute=30, second=0)
        )
        
        self.scheduler.add_job(
            market_hours_wrapper,
            trigger=trigger,
            id=job_id,
            name=f"MarketHours: {job_id}",
            replace_existing=True,
            **kwargs
        )
        
        self._registered_jobs[job_id] = {
            'type': 'market_hours',
            'schedule': f'Every {interval_minutes}min during market hours'
        }
        logger.info(f"Registered market-hours job: {job_id} every {interval_minutes}min")
    
    def add_post_market_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = 16,
        minute: int = 30,
        **kwargs
    ) -> None:
        """
        Add a job that runs after market close (default 4:30 PM ET).
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            hour: Hour to run (ET timezone)
            minute: Minute to run
            **kwargs: Additional arguments for the job
        """
        if not self.scheduler:
            self.initialize()
        
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week='mon-fri',
            timezone='America/New_York'
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=f"PostMarket: {job_id}",
            replace_existing=True,
            **kwargs
        )
        
        self._registered_jobs[job_id] = {
            'type': 'post_market',
            'schedule': f'{hour:02d}:{minute:02d} ET Mon-Fri'
        }
        logger.info(f"Registered post-market job: {job_id} at {hour:02d}:{minute:02d} ET")
    
    def add_weekly_job(
        self,
        job_id: str,
        func: Callable,
        day_of_week: str = 'fri',
        hour: int = 18,
        minute: int = 0,
        **kwargs
    ) -> None:
        """
        Add a weekly job (e.g., weekly report).
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            day_of_week: Day to run (mon, tue, wed, thu, fri, sat, sun)
            hour: Hour to run (ET timezone)
            minute: Minute to run
            **kwargs: Additional arguments for the job
        """
        if not self.scheduler:
            self.initialize()
        
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone='America/New_York'
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=f"Weekly: {job_id}",
            replace_existing=True,
            **kwargs
        )
        
        self._registered_jobs[job_id] = {
            'type': 'weekly',
            'schedule': f'{day_of_week.capitalize()} {hour:02d}:{minute:02d} ET'
        }
        logger.info(f"Registered weekly job: {job_id} on {day_of_week} at {hour:02d}:{minute:02d} ET")
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: int = None,
        minutes: int = None,
        hours: int = None,
        **kwargs
    ) -> None:
        """
        Add a job that runs at a fixed interval (any time).
        
        Args:
            job_id: Unique identifier for the job
            func: Async function to execute
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            **kwargs: Additional arguments for the job
        """
        if not self.scheduler:
            self.initialize()
        
        trigger = IntervalTrigger(
            seconds=seconds,
            minutes=minutes,
            hours=hours
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=f"Interval: {job_id}",
            replace_existing=True,
            **kwargs
        )
        
        interval_str = []
        if hours:
            interval_str.append(f"{hours}h")
        if minutes:
            interval_str.append(f"{minutes}m")
        if seconds:
            interval_str.append(f"{seconds}s")
        
        self._registered_jobs[job_id] = {
            'type': 'interval',
            'schedule': f'Every {" ".join(interval_str)}'
        }
        logger.info(f"Registered interval job: {job_id} every {' '.join(interval_str)}")
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
                self._registered_jobs.pop(job_id, None)
                logger.info(f"Removed job: {job_id}")
                return True
            except Exception as e:
                logger.warning(f"Failed to remove job {job_id}: {e}")
        return False
    
    def get_jobs_status(self) -> dict:
        """Get status of all registered jobs."""
        status = {
            'is_running': self._is_running,
            'jobs': {}
        }
        
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                status['jobs'][job.id] = {
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'pending': job.pending,
                    **self._registered_jobs.get(job.id, {})
                }
        
        return status


# Singleton instance
_bot_scheduler: Optional[BotScheduler] = None


def get_bot_scheduler() -> BotScheduler:
    """Get the singleton bot scheduler instance."""
    global _bot_scheduler
    if _bot_scheduler is None:
        _bot_scheduler = BotScheduler()
    return _bot_scheduler
