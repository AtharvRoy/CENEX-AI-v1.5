"""Pydantic schemas for market data API."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class OHLCVData(BaseModel):
    """Single OHLCV data point."""
    
    timestamp: datetime
    open: Decimal = Field(..., description="Opening price")
    high: Decimal = Field(..., description="Highest price")
    low: Decimal = Field(..., description="Lowest price")
    close: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    adj_close: Optional[Decimal] = Field(None, description="Adjusted closing price")
    
    class Config:
        from_attributes = True


class OHLCVResponse(BaseModel):
    """Response for OHLCV data endpoint."""
    
    symbol: str
    data: List[OHLCVData]
    count: int
    timeframe: str  # 1m, 5m, 15m, 1h, 1d
    from_cache: bool = False
    
    class Config:
        from_attributes = True


class LatestPriceResponse(BaseModel):
    """Latest price for a symbol."""
    
    symbol: str
    price: Decimal
    timestamp: datetime
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: int
    from_cache: bool = False
    
    class Config:
        from_attributes = True


class WatchlistRequest(BaseModel):
    """Request for multiple symbols."""
    
    symbols: List[str] = Field(..., description="List of symbols to fetch")


class WatchlistResponse(BaseModel):
    """Response for watchlist endpoint."""
    
    data: List[LatestPriceResponse]
    count: int
    
    class Config:
        from_attributes = True


class BackfillRequest(BaseModel):
    """Request to backfill historical data."""
    
    symbol: Optional[str] = Field(None, description="Specific symbol or None for all active")
    days: int = Field(90, ge=1, le=730, description="Number of days to backfill (1-730)")
    overwrite: bool = Field(False, description="Overwrite existing data")


class BackfillResponse(BaseModel):
    """Response for backfill operation."""
    
    status: str
    message: str
    symbols_queued: List[str]
    task_id: Optional[str] = None
