"""
Market Data Service - Yahoo Finance integration with caching.
Handles fetching OHLCV data, caching in Redis, and storing in TimescaleDB.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
import json

import yfinance as yf
import pandas as pd
import redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.market_data import MarketData
from app.schemas.market_data import OHLCVData, LatestPriceResponse

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and managing market data."""
    
    CACHE_TTL_LATEST = 300  # 5 minutes for latest prices
    CACHE_TTL_OHLCV = 900   # 15 minutes for OHLCV data
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    async def fetch_latest_price(self, symbol: str) -> Optional[LatestPriceResponse]:
        """
        Fetch latest price for a symbol.
        Checks cache first, then Yahoo Finance, then database.
        """
        # Check cache
        cache_key = f"price:latest:{symbol}"
        cached = self.redis.get(cache_key)
        
        if cached:
            try:
                data = json.loads(cached)
                return LatestPriceResponse(
                    symbol=symbol,
                    price=Decimal(str(data['price'])),
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    change=Decimal(str(data['change'])) if data.get('change') else None,
                    change_percent=Decimal(str(data['change_percent'])) if data.get('change_percent') else None,
                    volume=data['volume'],
                    from_cache=True
                )
            except Exception as e:
                logger.warning(f"Failed to parse cached data for {symbol}: {e}")
        
        # Fetch from Yahoo Finance
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                logger.warning(f"No data from Yahoo Finance for {symbol}")
                return await self._fetch_from_db(symbol)
            
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Close']
            
            change = latest['Close'] - prev_close
            change_percent = (change / prev_close * 100) if prev_close != 0 else 0
            
            response = LatestPriceResponse(
                symbol=symbol,
                price=Decimal(str(latest['Close'])),
                timestamp=latest.name.to_pydatetime(),
                change=Decimal(str(change)),
                change_percent=Decimal(str(change_percent)),
                volume=int(latest['Volume']),
                from_cache=False
            )
            
            # Cache the result
            cache_data = {
                'price': float(response.price),
                'timestamp': response.timestamp.isoformat(),
                'change': float(response.change) if response.change else None,
                'change_percent': float(response.change_percent) if response.change_percent else None,
                'volume': response.volume
            }
            self.redis.setex(cache_key, self.CACHE_TTL_LATEST, json.dumps(cache_data))
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to fetch latest price from Yahoo Finance for {symbol}: {e}")
            return await self._fetch_from_db(symbol)
    
    async def _fetch_from_db(self, symbol: str) -> Optional[LatestPriceResponse]:
        """Fetch latest price from database as fallback."""
        try:
            stmt = select(MarketData).where(
                MarketData.symbol == symbol
            ).order_by(desc(MarketData.timestamp)).limit(2)
            
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            
            if not rows:
                return None
            
            latest = rows[0]
            prev = rows[1] if len(rows) > 1 else latest
            
            change = latest.close - prev.close
            change_percent = (change / prev.close * 100) if prev.close != 0 else 0
            
            return LatestPriceResponse(
                symbol=symbol,
                price=latest.close,
                timestamp=latest.timestamp,
                change=change,
                change_percent=change_percent,
                volume=latest.volume,
                from_cache=False
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch from database for {symbol}: {e}")
            return None
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data for a symbol within a date range.
        Checks cache first, then database, then Yahoo Finance.
        """
        # Generate cache key
        cache_key = f"ohlcv:{symbol}:{interval}:{start_date.date()}:{end_date.date()}"
        cached = self.redis.get(cache_key)
        
        if cached:
            try:
                data = json.loads(cached)
                return [
                    OHLCVData(
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        open=Decimal(str(item['open'])),
                        high=Decimal(str(item['high'])),
                        low=Decimal(str(item['low'])),
                        close=Decimal(str(item['close'])),
                        volume=item['volume'],
                        adj_close=Decimal(str(item['adj_close'])) if item.get('adj_close') else None
                    )
                    for item in data
                ]
            except Exception as e:
                logger.warning(f"Failed to parse cached OHLCV for {symbol}: {e}")
        
        # Fetch from database
        try:
            stmt = select(MarketData).where(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.timestamp >= start_date,
                    MarketData.timestamp <= end_date
                )
            ).order_by(MarketData.timestamp)
            
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            
            if rows:
                ohlcv_data = [
                    OHLCVData(
                        timestamp=row.timestamp,
                        open=row.open,
                        high=row.high,
                        low=row.low,
                        close=row.close,
                        volume=row.volume,
                        adj_close=row.adj_close
                    )
                    for row in rows
                ]
                
                # Cache the result
                cache_data = [
                    {
                        'timestamp': item.timestamp.isoformat(),
                        'open': float(item.open),
                        'high': float(item.high),
                        'low': float(item.low),
                        'close': float(item.close),
                        'volume': item.volume,
                        'adj_close': float(item.adj_close) if item.adj_close else None
                    }
                    for item in ohlcv_data
                ]
                self.redis.setex(cache_key, self.CACHE_TTL_OHLCV, json.dumps(cache_data))
                
                return ohlcv_data
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV from database for {symbol}: {e}")
        
        # If no data in DB, return empty (ingestion pipeline will handle fetching)
        return []
    
    async def get_watchlist(self, symbols: List[str]) -> List[LatestPriceResponse]:
        """Fetch latest prices for multiple symbols."""
        results = []
        for symbol in symbols:
            price_data = await self.fetch_latest_price(symbol)
            if price_data:
                results.append(price_data)
        return results
    
    def validate_ohlcv(self, data: Dict[str, Any]) -> bool:
        """
        Validate OHLCV data for sanity.
        Returns True if valid, False otherwise.
        """
        try:
            open_price = float(data['open'])
            high = float(data['high'])
            low = float(data['low'])
            close = float(data['close'])
            volume = int(data['volume'])
            
            # Price sanity checks
            if high < low:
                logger.warning(f"Invalid data: high < low")
                return False
            
            if high < open_price or high < close:
                logger.warning(f"Invalid data: high < open or close")
                return False
            
            if low > open_price or low > close:
                logger.warning(f"Invalid data: low > open or close")
                return False
            
            if volume < 0:
                logger.warning(f"Invalid data: negative volume")
                return False
            
            # Price reasonableness (positive values)
            if any(p <= 0 for p in [open_price, high, low, close]):
                logger.warning(f"Invalid data: non-positive prices")
                return False
            
            return True
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Validation error: {e}")
            return False
