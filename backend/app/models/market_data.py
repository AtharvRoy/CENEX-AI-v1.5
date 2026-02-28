"""Market data models for OHLCV data and ingestion logs."""

from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MarketData(Base):
    """OHLCV market data - will be converted to TimescaleDB hypertable."""
    
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(20, 4), nullable=False)
    high = Column(Numeric(20, 4), nullable=False)
    low = Column(Numeric(20, 4), nullable=False)
    close = Column(Numeric(20, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    adj_close = Column(Numeric(20, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        {'postgresql_partition_by': 'RANGE (timestamp)'}  # For future partitioning
    )
    
    def __repr__(self):
        return f"<MarketData {self.symbol} @ {self.timestamp}>"


class DataIngestionLog(Base):
    """Log of data ingestion operations."""
    
    __tablename__ = "data_ingestion_log"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # yahoo, nse, bse
    records_inserted = Column(Integer)
    status = Column(String(20), index=True)  # success, partial, failed
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<DataIngestionLog {self.symbol} - {self.status}>"
