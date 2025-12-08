"""
Trading Assistant Bot

An ADVISORY-only bot that assists with trading operations:
- Analyzes market conditions (pre-market, during session)
- Monitors positions and generates alerts
- Creates trade suggestions (user must execute manually)
- Generates daily/weekly reports

IMPORTANT: This bot does NOT execute any trades automatically.
All actions are suggestions that require user confirmation.
"""
from app.bot.scheduler import BotScheduler, get_bot_scheduler
from app.bot.signal_engine import SignalEngine, get_signal_engine
from app.bot.analyzers import (
    PreMarketAnalyzer,
    PositionMonitor,
    ReportGenerator,
    run_pre_market_analysis_for_all_users,
    run_position_monitor_for_all_users,
    run_daily_reports_for_all_users,
    run_weekly_reports_for_all_users,
)

__all__ = [
    # Scheduler
    "BotScheduler",
    "get_bot_scheduler",
    
    # Signal Engine
    "SignalEngine",
    "get_signal_engine",
    
    # Analyzers
    "PreMarketAnalyzer",
    "PositionMonitor",
    "ReportGenerator",
    
    # Scheduled Tasks
    "run_pre_market_analysis_for_all_users",
    "run_position_monitor_for_all_users",
    "run_daily_reports_for_all_users",
    "run_weekly_reports_for_all_users",
    
    # Bot Initialization
    "initialize_bot",
    "shutdown_bot",
]


async def initialize_bot() -> BotScheduler:
    """
    Initialize and start the Trading Assistant Bot.
    
    Sets up scheduled jobs:
    - Pre-market analysis: 6:00 AM ET Mon-Fri
    - Position monitoring: Every 5 min during market hours
    - Daily summary: 4:30 PM ET Mon-Fri
    - Weekly report: Friday 6:00 PM ET
    - Signal cleanup: Every hour
    
    Returns:
        BotScheduler instance
    """
    from loguru import logger
    from app.db.database import get_db
    
    scheduler = get_bot_scheduler()
    scheduler.initialize()
    
    # Pre-market analysis job
    async def pre_market_job():
        async for db in get_db():
            await run_pre_market_analysis_for_all_users(db)
    
    scheduler.add_pre_market_job(
        job_id="pre_market_analysis",
        func=pre_market_job,
        hour=6,
        minute=0
    )
    
    # Position monitoring job (during market hours)
    async def position_monitor_job():
        async for db in get_db():
            await run_position_monitor_for_all_users(db)
    
    scheduler.add_market_hours_job(
        job_id="position_monitor",
        func=position_monitor_job,
        interval_minutes=5
    )
    
    # Daily summary job (after market close)
    async def daily_summary_job():
        async for db in get_db():
            await run_daily_reports_for_all_users(db)
    
    scheduler.add_post_market_job(
        job_id="daily_summary",
        func=daily_summary_job,
        hour=16,
        minute=30
    )
    
    # Weekly report job
    async def weekly_report_job():
        async for db in get_db():
            await run_weekly_reports_for_all_users(db)
    
    scheduler.add_weekly_job(
        job_id="weekly_report",
        func=weekly_report_job,
        day_of_week='fri',
        hour=18,
        minute=0
    )
    
    # Signal cleanup job (expire old signals)
    async def cleanup_signals_job():
        from app.bot.signal_engine import SignalEngine
        async for db in get_db():
            engine = SignalEngine(db)
            await engine.expire_old_signals()
    
    scheduler.add_interval_job(
        job_id="signal_cleanup",
        func=cleanup_signals_job,
        hours=1
    )
    
    # Start the scheduler
    scheduler.start()
    
    logger.info("Trading Assistant Bot initialized and running")
    logger.info(f"Jobs scheduled: {list(scheduler._registered_jobs.keys())}")
    
    return scheduler


async def shutdown_bot():
    """Gracefully shutdown the Trading Assistant Bot."""
    from loguru import logger
    
    scheduler = get_bot_scheduler()
    scheduler.stop()
    
    logger.info("Trading Assistant Bot shutdown complete")
