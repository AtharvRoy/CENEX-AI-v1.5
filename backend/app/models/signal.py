"""
Signal model for AI-generated trading signals.
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Signal(Base):
    """Trading signal model (Layer 4 Meta Decision Engine output)."""
    
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)  # NSE, BSE
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    price_entry: Mapped[float] = mapped_column(Float, nullable=True)
    price_target: Mapped[float] = mapped_column(Float, nullable=True)
    price_stoploss: Mapped[float] = mapped_column(Float, nullable=True)
    reasoning: Mapped[dict] = mapped_column(JSON, nullable=True)  # agent outputs, feature importance
    regime: Mapped[str] = mapped_column(String(50), nullable=True)  # high_vol, low_vol, trending, ranging
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="signal")
    performances: Mapped[list["SignalPerformance"]] = relationship("SignalPerformance", back_populates="signal", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, symbol='{self.symbol}', type='{self.signal_type}', confidence={self.confidence:.2f})>"
