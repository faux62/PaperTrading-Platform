#!/usr/bin/env python3
"""
Historical Data Downloader

Downloads 5 years of historical OHLCV data for all symbols in market_universe.
Uses yfinance with batch downloading for efficiency.

Usage:
    python scripts/download_historical_data.py
    
    # Or with custom settings:
    python scripts/download_historical_data.py --years 3 --batch-size 100
"""
import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import yfinance as yf
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent to path for imports
sys.path.insert(0, '/app')

from app.db.database import get_db


# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)


async def get_all_symbols(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get all active symbols from market_universe with their yfinance suffix."""
    query = text("""
        SELECT symbol, currency, exchange, region
        FROM market_universe
        WHERE is_active = true
        ORDER BY symbol
    """)
    result = await db.execute(query)
    rows = result.fetchall()
    
    symbols = []
    for row in rows:
        symbol = row[0]
        currency = row[1]
        exchange = row[2]
        
        # Add yfinance suffix based on exchange/currency
        yf_symbol = symbol
        if exchange == 'LSE' or currency == 'GBP':
            if not symbol.endswith('.L'):
                yf_symbol = f"{symbol}.L"
        elif exchange == 'XETRA' or (currency == 'EUR' and 'DE' in str(exchange or '')):
            if not symbol.endswith('.DE'):
                yf_symbol = f"{symbol}.DE"
        elif exchange in ['EURONEXT', 'EPA'] or symbol.endswith('.PA'):
            if not symbol.endswith('.PA'):
                yf_symbol = f"{symbol}.PA"
        elif exchange == 'BIT' or symbol.endswith('.MI'):
            if not symbol.endswith('.MI'):
                yf_symbol = f"{symbol}.MI"
        elif exchange == 'BME' or symbol.endswith('.MC'):
            if not symbol.endswith('.MC'):
                yf_symbol = f"{symbol}.MC"
        elif exchange == 'SIX' or currency == 'CHF':
            if not symbol.endswith('.SW'):
                yf_symbol = f"{symbol}.SW"
        elif currency == 'JPY':
            if not symbol.endswith('.T'):
                yf_symbol = f"{symbol}.T"
        elif currency == 'HKD':
            if not symbol.endswith('.HK'):
                yf_symbol = f"{symbol}.HK"
        
        symbols.append({
            'symbol': symbol,  # Original symbol for DB
            'yf_symbol': yf_symbol,  # Yahoo Finance symbol
            'currency': currency,
            'exchange': exchange
        })
    
    return symbols


async def delete_existing_data(db: AsyncSession, symbols: List[str]) -> int:
    """Delete existing data for symbols to avoid duplicates."""
    if not symbols:
        return 0
    
    # Delete in batches to avoid query size limits
    deleted = 0
    batch_size = 100
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        placeholders = ', '.join([f"'{s}'" for s in batch])
        query = text(f"DELETE FROM price_bars WHERE symbol IN ({placeholders})")
        result = await db.execute(query)
        deleted += result.rowcount
    
    await db.commit()
    return deleted


async def insert_bars(db: AsyncSession, symbol: str, df: pd.DataFrame) -> int:
    """Insert OHLCV bars into price_bars table."""
    if df.empty:
        return 0
    
    inserted = 0
    batch_size = 500
    
    # Prepare data
    rows = []
    for idx, row in df.iterrows():
        timestamp = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx
        rows.append({
            'symbol': symbol,
            'timeframe': 'D1',  # Enum value for daily
            'timestamp': timestamp,
            'open': float(row['Open']) if pd.notna(row['Open']) else None,
            'high': float(row['High']) if pd.notna(row['High']) else None,
            'low': float(row['Low']) if pd.notna(row['Low']) else None,
            'close': float(row['Close']) if pd.notna(row['Close']) else None,
            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
            'adjusted_close': float(row.get('Adj Close', row['Close'])) if pd.notna(row.get('Adj Close', row['Close'])) else None,
            'source': 'yfinance'
        })
    
    # Insert in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        
        values_list = []
        for r in batch:
            ts = r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            values_list.append(
                f"('{r['symbol']}', 'D1', '{ts}', "
                f"{r['open'] if r['open'] else 'NULL'}, "
                f"{r['high'] if r['high'] else 'NULL'}, "
                f"{r['low'] if r['low'] else 'NULL'}, "
                f"{r['close'] if r['close'] else 'NULL'}, "
                f"{r['volume']}, "
                f"{r['adjusted_close'] if r['adjusted_close'] else 'NULL'}, "
                f"'{r['source']}')"
            )
        
        query = text(f"""
            INSERT INTO price_bars 
            (symbol, timeframe, timestamp, open, high, low, close, volume, adjusted_close, source)
            VALUES {', '.join(values_list)}
            ON CONFLICT DO NOTHING
        """)
        
        try:
            await db.execute(query)
            inserted += len(batch)
        except Exception as e:
            logger.warning(f"Insert error for {symbol}: {e}")
    
    return inserted


def download_batch(yf_symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """Download historical data for a batch of symbols using yfinance."""
    try:
        # Join symbols with space for yfinance
        symbols_str = ' '.join(yf_symbols)
        
        # Download with progress disabled for cleaner output
        data = yf.download(
            symbols_str,
            start=start_date,
            end=end_date,
            progress=False,
            threads=True,
            group_by='ticker'
        )
        
        result = {}
        
        if len(yf_symbols) == 1:
            # Single symbol returns different format
            if not data.empty:
                result[yf_symbols[0]] = data
        else:
            # Multiple symbols - data is grouped by ticker
            for symbol in yf_symbols:
                try:
                    if symbol in data.columns.get_level_values(0):
                        df = data[symbol].dropna(how='all')
                        if not df.empty:
                            result[symbol] = df
                except Exception:
                    pass
        
        return result
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return {}


async def main(years: int = 5, batch_size: int = 50, skip_delete: bool = False):
    """Main function to download historical data."""
    
    logger.info(f"=" * 60)
    logger.info(f"Historical Data Downloader")
    logger.info(f"Years: {years} | Batch size: {batch_size}")
    logger.info(f"=" * 60)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    
    stats = {
        'total_symbols': 0,
        'successful': 0,
        'failed': 0,
        'bars_inserted': 0,
        'bars_deleted': 0
    }
    
    async for db in get_db():
        # Get all symbols
        symbols_data = await get_all_symbols(db)
        stats['total_symbols'] = len(symbols_data)
        
        logger.info(f"Found {stats['total_symbols']} symbols in market_universe")
        
        if not skip_delete:
            # Delete existing data
            logger.info("Deleting existing data...")
            all_symbols = [s['symbol'] for s in symbols_data]
            deleted = await delete_existing_data(db, all_symbols)
            stats['bars_deleted'] = deleted
            logger.info(f"Deleted {deleted:,} existing bars")
        
        # Create mapping from yf_symbol to original symbol
        yf_to_original = {s['yf_symbol']: s['symbol'] for s in symbols_data}
        yf_symbols = [s['yf_symbol'] for s in symbols_data]
        
        # Process in batches
        total_batches = (len(yf_symbols) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(yf_symbols), batch_size):
            batch_num = batch_idx // batch_size + 1
            batch = yf_symbols[batch_idx:batch_idx + batch_size]
            
            logger.info(f"Batch {batch_num}/{total_batches}: Downloading {len(batch)} symbols...")
            
            # Download data
            downloaded = download_batch(
                batch,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            # Insert into database
            batch_inserted = 0
            batch_success = 0
            batch_failed = 0
            
            for yf_symbol, df in downloaded.items():
                original_symbol = yf_to_original.get(yf_symbol, yf_symbol)
                
                try:
                    inserted = await insert_bars(db, original_symbol, df)
                    batch_inserted += inserted
                    batch_success += 1
                except Exception as e:
                    logger.warning(f"Failed to insert {original_symbol}: {e}")
                    batch_failed += 1
            
            # Count symbols that didn't return data
            batch_failed += len(batch) - len(downloaded)
            
            await db.commit()
            
            stats['successful'] += batch_success
            stats['failed'] += batch_failed
            stats['bars_inserted'] += batch_inserted
            
            logger.info(
                f"  → Success: {batch_success}, Failed: {len(batch) - batch_success}, "
                f"Bars: {batch_inserted:,}"
            )
            
            # Small delay between batches to avoid rate limiting
            if batch_idx + batch_size < len(yf_symbols):
                await asyncio.sleep(1)
        
        break
    
    # Final report
    logger.info(f"=" * 60)
    logger.info(f"DOWNLOAD COMPLETE")
    logger.info(f"=" * 60)
    logger.info(f"Total symbols: {stats['total_symbols']}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Bars deleted: {stats['bars_deleted']:,}")
    logger.info(f"Bars inserted: {stats['bars_inserted']:,}")
    logger.info(f"Avg bars per symbol: {stats['bars_inserted'] // max(stats['successful'], 1)}")
    
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download historical OHLCV data')
    parser.add_argument('--years', type=int, default=5, help='Years of history to download')
    parser.add_argument('--batch-size', type=int, default=50, help='Symbols per batch')
    parser.add_argument('--skip-delete', action='store_true', help='Skip deleting existing data')
    
    args = parser.parse_args()
    
    asyncio.run(main(
        years=args.years,
        batch_size=args.batch_size,
        skip_delete=args.skip_delete
    ))
