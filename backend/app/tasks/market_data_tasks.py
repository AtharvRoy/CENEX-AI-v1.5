"""
Celery tasks for market data ingestion.
Handles scheduled updates and historical backfills.
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)

# Create async engine for tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    """Get database session for async tasks."""
    async with AsyncSessionLocal() as session:
        yield session


@celery_app.task(name='app.tasks.market_data_tasks.update_market_data', bind=True)
def update_market_data(self):
    """
    Scheduled task: Update market data for all active symbols.
    Runs every 15 minutes during market hours.
    """
    import asyncio
    
    async def _update():
        async with AsyncSessionLocal() as session:
            service = DataIngestionService(session)
            results = await service.update_all_active_symbols()
            
            success_count = sum(1 for _, (_, status) in results.items() if status == "success")
            total_records = sum(count for _, (count, _) in results.items())
            
            logger.info(f"Market data update completed: {success_count}/{len(results)} symbols, {total_records} records")
            
            return {
                'success_count': success_count,
                'total_symbols': len(results),
                'total_records': total_records,
                'results': {k: {'count': v[0], 'status': v[1]} for k, v in results.items()}
            }
    
    # Run async function in event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running (nested), use asyncio.run in thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _update())
            result = future.result()
    else:
        result = asyncio.run(_update())
    
    return result


@celery_app.task(name='app.tasks.market_data_tasks.backfill_historical_data', bind=True)
def backfill_historical_data(self, symbol: str, days: int = 90, overwrite: bool = False):
    """
    Manual task: Backfill historical data for a specific symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE.NS')
        days: Number of days to backfill
        overwrite: Whether to overwrite existing data
    """
    import asyncio
    
    async def _backfill():
        async with AsyncSessionLocal() as session:
            service = DataIngestionService(session)
            count, status = await service.backfill_symbol(symbol, days=days, overwrite=overwrite)
            
            logger.info(f"Backfill completed for {symbol}: {count} records, status={status}")
            
            return {
                'symbol': symbol,
                'records_inserted': count,
                'status': status,
                'days': days
            }
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _backfill())
            result = future.result()
    else:
        result = asyncio.run(_backfill())
    
    return result


@celery_app.task(name='app.tasks.market_data_tasks.backfill_all_symbols', bind=True)
def backfill_all_symbols(self, days: int = 90):
    """
    Manual task: Backfill historical data for all active symbols.
    
    Args:
        days: Number of days to backfill
    """
    import asyncio
    
    async def _backfill_all():
        async with AsyncSessionLocal() as session:
            service = DataIngestionService(session)
            results = await service.backfill_all_active_symbols(days=days)
            
            success_count = sum(1 for _, (_, status) in results.items() if status == "success")
            total_records = sum(count for _, (count, _) in results.items())
            
            logger.info(f"Backfill all completed: {success_count}/{len(results)} symbols, {total_records} records")
            
            return {
                'success_count': success_count,
                'total_symbols': len(results),
                'total_records': total_records,
                'days': days,
                'results': {k: {'count': v[0], 'status': v[1]} for k, v in results.items()}
            }
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _backfill_all())
            result = future.result()
    else:
        result = asyncio.run(_backfill_all())
    
    return result
