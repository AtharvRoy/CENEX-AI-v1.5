"""
Data Ingestion Service - Historical backfill and incremental updates.
Handles batch ingestion from Yahoo Finance into TimescaleDB.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import asyncio

import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.market_data import MarketData, DataIngestionLog
from app.models.symbol import Symbol
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Service for ingesting historical and real-time market data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def backfill_symbol(
        self,
        symbol: str,
        days: int = 90,
        overwrite: bool = False
    ) -> Tuple[int, str]:
        """
        Backfill historical data for a single symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            days: Number of days to backfill
            overwrite: If True, overwrite existing data
        
        Returns:
            Tuple of (records_inserted, status)
        """
        log_entry = DataIngestionLog(
            symbol=symbol,
            source="yahoo",
            started_at=datetime.utcnow(),
            status="running"
        )
        self.db.add(log_entry)
        await self.db.commit()
        
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Backfilling {symbol} from {start_date.date()} to {end_date.date()}")
            
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if hist.empty:
                logger.warning(f"No data returned from Yahoo Finance for {symbol}")
                log_entry.status = "failed"
                log_entry.error_message = "No data returned from Yahoo Finance"
                log_entry.completed_at = datetime.utcnow()
                log_entry.records_inserted = 0
                await self.db.commit()
                return 0, "failed"
            
            # Prepare data for insertion
            records = []
            valid_count = 0
            
            for timestamp, row in hist.iterrows():
                # Validate data
                data_dict = {
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row['Volume']
                }
                
                if not MarketDataService(self.db, None).validate_ohlcv(data_dict):
                    logger.warning(f"Skipping invalid data for {symbol} at {timestamp}")
                    continue
                
                records.append({
                    'symbol': symbol,
                    'timestamp': timestamp.to_pydatetime(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'adj_close': float(row['Close']) if 'Close' in row else None,
                    'created_at': datetime.utcnow()
                })
                valid_count += 1
            
            if not records:
                logger.warning(f"No valid records to insert for {symbol}")
                log_entry.status = "failed"
                log_entry.error_message = "No valid records after validation"
                log_entry.completed_at = datetime.utcnow()
                log_entry.records_inserted = 0
                await self.db.commit()
                return 0, "failed"
            
            # Insert data with upsert logic (avoid duplicates)
            if overwrite:
                # Simple insert with ON CONFLICT DO UPDATE
                stmt = pg_insert(MarketData).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timestamp'],
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                        'adj_close': stmt.excluded.adj_close,
                    }
                )
                await self.db.execute(stmt)
            else:
                # Insert only if not exists
                stmt = pg_insert(MarketData).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['symbol', 'timestamp']
                )
                await self.db.execute(stmt)
            
            await self.db.commit()
            
            # Update log
            log_entry.status = "success"
            log_entry.records_inserted = valid_count
            log_entry.completed_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"Successfully backfilled {valid_count} records for {symbol}")
            return valid_count, "success"
            
        except Exception as e:
            logger.error(f"Error backfilling {symbol}: {e}", exc_info=True)
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.completed_at = datetime.utcnow()
            log_entry.records_inserted = 0
            await self.db.commit()
            return 0, "failed"
    
    async def backfill_all_active_symbols(self, days: int = 90) -> Dict[str, Tuple[int, str]]:
        """
        Backfill all active symbols in the database.
        
        Args:
            days: Number of days to backfill
        
        Returns:
            Dict mapping symbol to (records_inserted, status)
        """
        # Fetch all active symbols
        stmt = select(Symbol).where(Symbol.is_active == True)
        result = await self.db.execute(stmt)
        symbols = result.scalars().all()
        
        if not symbols:
            logger.warning("No active symbols found in database")
            return {}
        
        logger.info(f"Starting backfill for {len(symbols)} symbols")
        
        results = {}
        for symbol_obj in symbols:
            symbol = symbol_obj.symbol
            count, status = await self.backfill_symbol(symbol, days=days, overwrite=False)
            results[symbol] = (count, status)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return results
    
    async def incremental_update(self, symbol: str) -> Tuple[int, str]:
        """
        Perform incremental update for a symbol (fetch latest data).
        Fetches data from the last known timestamp to now.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Tuple of (records_inserted, status)
        """
        try:
            # Find the latest timestamp we have for this symbol
            stmt = select(MarketData.timestamp).where(
                MarketData.symbol == symbol
            ).order_by(MarketData.timestamp.desc()).limit(1)
            
            result = await self.db.execute(stmt)
            last_timestamp = result.scalar()
            
            if last_timestamp:
                start_date = last_timestamp
            else:
                # If no data exists, backfill last 7 days
                start_date = datetime.utcnow() - timedelta(days=7)
            
            end_date = datetime.utcnow()
            
            # Fetch new data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval="15m")
            
            if hist.empty:
                return 0, "no_new_data"
            
            # Prepare records
            records = []
            for timestamp, row in hist.iterrows():
                data_dict = {
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row['Volume']
                }
                
                if not MarketDataService(self.db, None).validate_ohlcv(data_dict):
                    continue
                
                records.append({
                    'symbol': symbol,
                    'timestamp': timestamp.to_pydatetime(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'adj_close': float(row['Close']) if 'Close' in row else None,
                    'created_at': datetime.utcnow()
                })
            
            if not records:
                return 0, "no_valid_data"
            
            # Upsert records
            stmt = pg_insert(MarketData).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['symbol', 'timestamp'])
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info(f"Incremental update: inserted {len(records)} records for {symbol}")
            return len(records), "success"
            
        except Exception as e:
            logger.error(f"Error in incremental update for {symbol}: {e}", exc_info=True)
            return 0, "failed"
    
    async def update_all_active_symbols(self) -> Dict[str, Tuple[int, str]]:
        """
        Perform incremental update for all active symbols.
        
        Returns:
            Dict mapping symbol to (records_inserted, status)
        """
        stmt = select(Symbol).where(Symbol.is_active == True)
        result = await self.db.execute(stmt)
        symbols = result.scalars().all()
        
        if not symbols:
            logger.warning("No active symbols found")
            return {}
        
        logger.info(f"Starting incremental update for {len(symbols)} symbols")
        
        results = {}
        for symbol_obj in symbols:
            symbol = symbol_obj.symbol
            count, status = await self.incremental_update(symbol)
            results[symbol] = (count, status)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.3)
        
        return results
    
    async def detect_gaps(self, symbol: str, start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        Detect missing timestamps (gaps) in market data.
        
        Args:
            symbol: Stock symbol
            start_date: Start of range
            end_date: End of range
        
        Returns:
            List of missing timestamps during market hours
        """
        # Fetch existing timestamps
        stmt = select(MarketData.timestamp).where(
            and_(
                MarketData.symbol == symbol,
                MarketData.timestamp >= start_date,
                MarketData.timestamp <= end_date
            )
        ).order_by(MarketData.timestamp)
        
        result = await self.db.execute(stmt)
        existing = [row[0] for row in result.all()]
        
        if not existing:
            return []
        
        # Generate expected timestamps (business days only)
        gaps = []
        current = existing[0]
        
        for i in range(1, len(existing)):
            next_ts = existing[i]
            expected_next = current + timedelta(days=1)
            
            # Check if there's a gap (more than 3 days, accounting for weekends)
            if (next_ts - current).days > 3:
                gaps.append(current)
            
            current = next_ts
        
        return gaps
    
    async def detect_volume_anomalies(self, symbol: str, threshold: float = 10.0) -> List[Dict]:
        """
        Detect volume anomalies (volume spikes).
        
        Args:
            symbol: Stock symbol
            threshold: Multiplier threshold (default 10x average)
        
        Returns:
            List of anomalies with timestamp and volume
        """
        # Fetch recent data (last 30 days)
        start_date = datetime.utcnow() - timedelta(days=30)
        
        stmt = select(MarketData).where(
            and_(
                MarketData.symbol == symbol,
                MarketData.timestamp >= start_date
            )
        ).order_by(MarketData.timestamp)
        
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        
        if len(rows) < 10:
            return []
        
        # Calculate average volume
        volumes = [row.volume for row in rows]
        avg_volume = sum(volumes) / len(volumes)
        
        # Find anomalies
        anomalies = []
        for row in rows:
            if row.volume > avg_volume * threshold:
                anomalies.append({
                    'timestamp': row.timestamp,
                    'volume': row.volume,
                    'avg_volume': avg_volume,
                    'multiplier': row.volume / avg_volume
                })
        
        return anomalies
