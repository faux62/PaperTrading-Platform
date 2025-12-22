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
import asyncio

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
    - Global price update: Every 1 minute (all markets, smart EOD caching)
    - Position monitoring: Every 5 min (alerts for significant changes)
    - Pre-market analysis: 6:00 AM ET Mon-Fri
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
    
    # ==========================================================
    # GLOBAL PRICE UPDATE JOB - Runs every minute for ALL markets
    # ==========================================================
    # This job handles:
    # - Real-time prices for open markets
    # - EOD prices for closed markets (fetched once per day)
    # - Smart caching to avoid redundant API calls
    async def global_price_update_job():
        from app.bot.services.global_price_updater import run_global_price_update
        
        async for db in get_db():
            stats = await run_global_price_update(db)
            if stats["positions_updated"] > 0:
                logger.info(
                    f"Global price update: {stats['positions_updated']} updated, "
                    f"{stats['positions_skipped']} skipped"
                )
    
    # Run every 5 minutes - NOT limited to US market hours
    scheduler.add_interval_job(
        job_id="global_price_update",
        func=global_price_update_job,
        minutes=5
    )
    
    # ==========================================================
    # POSITION MONITORING JOB - Alerts for all markets
    # ==========================================================
    async def position_monitor_job():
        async for db in get_db():
            await run_position_monitor_for_all_users(db)
    
    # Run every 5 minutes - NOT limited to US market hours
    scheduler.add_interval_job(
        job_id="position_monitor",
        func=position_monitor_job,
        minutes=5
    )
    
    # ==========================================================
    # PRE-MARKET ANALYSIS (US-focused but runs globally)
    # ==========================================================
    async def pre_market_job():
        async for db in get_db():
            await run_pre_market_analysis_for_all_users(db)
    
    scheduler.add_pre_market_job(
        job_id="pre_market_analysis",
        func=pre_market_job,
        hour=6,
        minute=0
    )
    
    # ==========================================================
    # DAILY SUMMARY (after US market close)
    # ==========================================================
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
    
    # ==========================================================
    # FX RATE UPDATE - Exchange rates from Frankfurter API (ECB)
    # ==========================================================
    # Updates EUR, USD, GBP, CHF rates every hour
    async def fx_rate_update_job():
        from app.services.fx_rate_updater import update_exchange_rates
        
        count = await update_exchange_rates()
        if count > 0:
            logger.info(f"FX rate update: {count} rates updated from Frankfurter API")
    
    scheduler.add_interval_job(
        job_id="fx_rate_update",
        func=fx_rate_update_job,
        hours=1
    )
    
    # Run FX update at startup if table is empty or data is stale (>1 hour)
    async def fx_rate_startup_check():
        from datetime import datetime, timedelta
        from sqlalchemy import select, func
        from app.db.models.exchange_rate import ExchangeRate
        
        async for db in get_db():
            # Check if table is empty
            result = await db.execute(select(func.count(ExchangeRate.id)))
            count = result.scalar()
            
            if count == 0:
                logger.info("FX rates table is empty - running initial update...")
                await fx_rate_update_job()
                return
            
            # Check if data is stale (last update > 1 hour ago)
            result = await db.execute(
                select(func.max(ExchangeRate.fetched_at))
            )
            last_fetch = result.scalar()
            
            if last_fetch is None or datetime.utcnow() - last_fetch > timedelta(hours=1):
                logger.info(f"FX rates are stale (last: {last_fetch}) - running update...")
                await fx_rate_update_job()
            else:
                logger.info(f"FX rates are fresh (last: {last_fetch}) - skipping startup update")
            break
    
    # Schedule startup check
    asyncio.create_task(fx_rate_startup_check())
    
    # ==========================================================
    # UNIVERSE DATA COLLECTION - ~900 symbols from major indices
    # ==========================================================
    # Quote updates for universe (every 5 min during market hours)
    async def universe_quote_update_job():
        from app.bot.services.universe_data_collector import run_universe_quote_update
        
        async for db in get_db():
            stats = await run_universe_quote_update(db)
            logger.info(
                f"Universe quote update: {stats['total']} total, {stats['updated']} updated, "
                f"{stats['failed']} failed"
            )
    
    scheduler.add_interval_job(
        job_id="universe_quote_update",
        func=universe_quote_update_job,
        minutes=5
    )
    
    # EOD data collection (daily at 11 PM UTC - after all markets close)
    async def universe_eod_collection_job():
        from app.bot.services.universe_data_collector import run_universe_eod_collection
        
        async for db in get_db():
            stats = await run_universe_eod_collection(db)
            logger.info(
                f"Universe EOD collection: {stats['updated']} symbols, "
                f"{stats['bars_inserted']} bars inserted"
            )
    
    scheduler.add_cron_job(
        job_id="universe_eod_collection",
        func=universe_eod_collection_job,
        hour=23,
        minute=0
    )
    
    # Check EOD data freshness at startup - run backfill if stale (>24h)
    async def eod_data_startup_check():
        from datetime import datetime, timedelta
        from sqlalchemy import select, func
        from app.db.models.price_bar import PriceBar
        
        async for db in get_db():
            # Check last EOD bar timestamp
            result = await db.execute(
                select(func.max(PriceBar.timestamp)).where(PriceBar.timeframe == "D1")
            )
            last_bar = result.scalar()
            
            if last_bar is None:
                logger.info("No EOD data found - running initial backfill...")
                await universe_eod_collection_job()
                return
            
            # If last bar is older than 24 hours, run EOD collection
            hours_since_update = (datetime.utcnow() - last_bar).total_seconds() / 3600
            
            if hours_since_update > 36:  # 36h to account for weekends
                logger.info(f"EOD data is stale (last: {last_bar}, {hours_since_update:.1f}h ago) - running update...")
                await universe_eod_collection_job()
            else:
                logger.info(f"EOD data is fresh (last: {last_bar}, {hours_since_update:.1f}h ago) - skipping startup update")
            break
    
    # Schedule EOD startup check (delay 30s to let other systems initialize)
    async def delayed_eod_check():
        await asyncio.sleep(30)
        await eod_data_startup_check()
    
    asyncio.create_task(delayed_eod_check())
    
    # Symbol enrichment (daily at 1 AM UTC - fill in missing names)
    async def symbol_enrichment_job():
        from app.bot.services.universe_data_collector import run_symbol_enrichment
        
        async for db in get_db():
            stats = await run_symbol_enrichment(db)
            if stats["updated"] > 0:
                logger.info(
                    f"Symbol enrichment: {stats['updated']} enriched"
                )
    
    scheduler.add_cron_job(
        job_id="symbol_enrichment",
        func=symbol_enrichment_job,
        hour=1,
        minute=0
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
