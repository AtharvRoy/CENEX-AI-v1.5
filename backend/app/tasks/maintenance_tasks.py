"""
Celery tasks for system maintenance.
Handles cache cleanup, data quality checks, and monitoring.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.data_ingestion import DataIngestionService
from app.models.symbol import Symbol
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Create async engine for tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(name='app.tasks.maintenance_tasks.cleanup_redis_cache', bind=True)
def cleanup_redis_cache(self):
    """
    Scheduled task: Clean up expired Redis cache entries.
    Runs daily at 2:00 AM IST.
    """
    try:
        # Get all keys matching our patterns
        patterns = ['price:latest:*', 'ohlcv:*']
        deleted_count = 0
        
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                deleted_count += redis_client.delete(*keys)
        
        logger.info(f"Redis cache cleanup: deleted {deleted_count} keys")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up Redis cache: {e}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@celery_app.task(name='app.tasks.maintenance_tasks.check_data_quality', bind=True)
def check_data_quality(self):
    """
    Scheduled task: Check data quality and detect anomalies.
    Runs daily at 4:00 PM IST (after market close).
    """
    import asyncio
    
    async def _check_quality():
        async with AsyncSessionLocal() as session:
            service = DataIngestionService(session)
            
            # Get all active symbols
            stmt = select(Symbol).where(Symbol.is_active == True)
            result = await session.execute(stmt)
            symbols = result.scalars().all()
            
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbols_checked': len(symbols),
                'gaps': {},
                'volume_anomalies': {}
            }
            
            # Check for gaps in data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            for symbol_obj in symbols[:10]:  # Check first 10 symbols to avoid timeout
                symbol = symbol_obj.symbol
                
                # Detect gaps
                gaps = await service.detect_gaps(symbol, start_date, end_date)
                if gaps:
                    report['gaps'][symbol] = [g.isoformat() for g in gaps]
                
                # Detect volume anomalies
                anomalies = await service.detect_volume_anomalies(symbol, threshold=10.0)
                if anomalies:
                    report['volume_anomalies'][symbol] = anomalies
            
            logger.info(f"Data quality check completed: {len(report['gaps'])} gaps, {len(report['volume_anomalies'])} anomalies")
            
            return report
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _check_quality())
            result = future.result()
    else:
        result = asyncio.run(_check_quality())
    
    return result
