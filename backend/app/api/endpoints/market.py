"""
Market data API endpoints.
Provides access to OHLCV data, latest prices, and watchlists.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import redis

from app.core.config import settings
from app.schemas.market_data import (
    OHLCVResponse,
    LatestPriceResponse,
    WatchlistRequest,
    WatchlistResponse,
    BackfillRequest,
    BackfillResponse
)
from app.services.market_data import MarketDataService
from app.tasks.market_data_tasks import backfill_historical_data, backfill_all_symbols

router = APIRouter()

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)


# Dependency to get database session
async def get_db():
    """Database session dependency (placeholder - will be implemented in Sprint 01)."""
    # This will be properly implemented when Sprint 01 provides the database session
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/{symbol}/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv_data(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe: 1m, 5m, 15m, 1h, 1d"),
    start_date: Optional[datetime] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get OHLCV (Open, High, Low, Close, Volume) data for a symbol.
    
    - **symbol**: Stock symbol (e.g., RELIANCE.NS)
    - **timeframe**: Data granularity (1m, 5m, 15m, 1h, 1d)
    - **start_date**: Start of date range
    - **end_date**: End of date range
    """
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Validate date range
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    # Validate timeframe
    valid_timeframes = ["1m", "5m", "15m", "1h", "1d"]
    if timeframe not in valid_timeframes:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe. Must be one of: {valid_timeframes}")
    
    # Fetch data
    service = MarketDataService(db, redis_client)
    data = await service.fetch_ohlcv(symbol, start_date, end_date, interval=timeframe)
    
    return OHLCVResponse(
        symbol=symbol,
        data=data,
        count=len(data),
        timeframe=timeframe,
        from_cache=False  # TODO: Track cache hits
    )


@router.get("/{symbol}/latest", response_model=LatestPriceResponse)
async def get_latest_price(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest price for a symbol.
    
    - **symbol**: Stock symbol (e.g., RELIANCE.NS)
    
    Returns the most recent price with change percentage.
    """
    service = MarketDataService(db, redis_client)
    price_data = await service.fetch_latest_price(symbol)
    
    if not price_data:
        raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
    
    return price_data


@router.post("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    request: WatchlistRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest prices for multiple symbols (watchlist).
    
    - **symbols**: List of stock symbols
    
    Returns latest price data for all requested symbols.
    """
    if not request.symbols:
        raise HTTPException(status_code=400, detail="symbols list cannot be empty")
    
    if len(request.symbols) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed per request")
    
    service = MarketDataService(db, redis_client)
    data = await service.get_watchlist(request.symbols)
    
    return WatchlistResponse(
        data=data,
        count=len(data)
    )


@router.post("/admin/backfill", response_model=BackfillResponse)
async def trigger_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger historical data backfill (admin only).
    
    - **symbol**: Specific symbol (optional, if None will backfill all active symbols)
    - **days**: Number of days to backfill (1-730)
    - **overwrite**: Whether to overwrite existing data
    
    This is an admin endpoint that triggers background tasks for data ingestion.
    """
    # TODO: Add authentication/authorization check (admin only)
    
    if request.symbol:
        # Backfill specific symbol
        task = backfill_historical_data.apply_async(
            args=[request.symbol, request.days, request.overwrite]
        )
        
        return BackfillResponse(
            status="queued",
            message=f"Backfill task queued for {request.symbol}",
            symbols_queued=[request.symbol],
            task_id=task.id
        )
    else:
        # Backfill all active symbols
        task = backfill_all_symbols.apply_async(args=[request.days])
        
        return BackfillResponse(
            status="queued",
            message="Backfill task queued for all active symbols",
            symbols_queued=["all"],
            task_id=task.id
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for market data service.
    """
    try:
        # Check Redis connection
        redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }
