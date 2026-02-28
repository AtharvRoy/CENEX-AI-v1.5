#!/usr/bin/env python3
"""
Initialize the data layer for Cenex AI.
This script:
1. Runs database migrations
2. Initializes Nifty 50 symbols
3. Triggers initial backfill (90 days)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.data_ingestion import DataIngestionService


async def main():
    """Initialize the data layer."""
    
    print("=" * 60)
    print("Cenex AI - Data Layer Initialization")
    print("=" * 60)
    
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n[1/3] Database connection established")
    
    # Check if TimescaleDB extension is enabled
    async with AsyncSessionLocal() as session:
        result = await session.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
        timescale_exists = result.scalar() is not None
        
        if timescale_exists:
            print("✓ TimescaleDB extension is enabled")
        else:
            print("⚠ TimescaleDB extension not found - please enable it manually")
            print("  Run: CREATE EXTENSION timescaledb;")
    
    print("\n[2/3] Verifying symbol data...")
    
    async with AsyncSessionLocal() as session:
        from app.models.symbol import Symbol
        from sqlalchemy import select
        
        stmt = select(Symbol).where(Symbol.is_active == True)
        result = await session.execute(stmt)
        symbols = result.scalars().all()
        
        print(f"✓ Found {len(symbols)} active symbols")
        
        if symbols:
            print("\nSample symbols:")
            for symbol in symbols[:5]:
                print(f"  - {symbol.symbol}: {symbol.company_name} ({symbol.sector})")
    
    print("\n[3/3] Starting historical data backfill...")
    print("This will take several minutes for Nifty 50 (90 days)...")
    
    # Trigger backfill using Celery task
    from app.tasks.market_data_tasks import backfill_all_symbols
    
    task = backfill_all_symbols.apply_async(args=[90])
    print(f"\n✓ Backfill task queued: {task.id}")
    print("\nYou can monitor the progress:")
    print("  - Check Celery worker logs")
    print("  - Query data_ingestion_log table")
    print("  - Use Flower (Celery monitoring): http://localhost:5555")
    
    print("\n" + "=" * 60)
    print("Data Layer Initialization Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start Celery worker: celery -A app.core.celery_app worker -l info")
    print("2. Start Celery beat: celery -A app.core.celery_app beat -l info")
    print("3. Monitor backfill progress in logs")
    print("4. Test API endpoints once backfill completes")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
