"""Symbol metadata model."""

from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Symbol(Base):
    """Symbol metadata for stocks and indices."""
    
    __tablename__ = "symbols"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(255))
    exchange = Column(String(20), nullable=False)  # NSE, BSE
    sector = Column(String(100))
    market_cap = Column(BigInteger)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Symbol {self.symbol} ({self.company_name})>"
