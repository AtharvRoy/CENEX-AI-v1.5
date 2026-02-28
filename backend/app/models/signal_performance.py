"""
Signal Performance model for Layer 6: Performance Memory.
Tracks outcomes of signals for self-learning loop.
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SignalPerformance(Base):
    """
    Signal performance tracking (Layer 6 - Performance Memory).
    This is the proprietary intelligence moat - learns from outcomes.
    """
    
    __tablename__ = "signal_performance"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    signal_id: Mapped[int] = mapped_column(Integer, ForeignKey("signals.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    regime: Mapped[str] = mapped_column(String(50), nullable=True)  # regime at signal time
    outcome: Mapped[str] = mapped_column(String(20), nullable=True)  # win, loss, breakeven, expired
    pnl_percent: Mapped[float] = mapped_column(Float, nullable=True)  # percentage return
    days_held: Mapped[int] = mapped_column(Integer, nullable=True)  # duration of trade
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    signal: Mapped["Signal"] = relationship("Signal", back_populates="performances")
    
    def __repr__(self) -> str:
        return f"<SignalPerformance(id={self.id}, signal_id={self.signal_id}, outcome='{self.outcome}', pnl={self.pnl_percent}%)>"
