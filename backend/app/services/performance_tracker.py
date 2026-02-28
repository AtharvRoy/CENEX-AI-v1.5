"""
Performance Tracker Service (Layer 6 - Performance Memory)

Tracks signal → trade → outcome lifecycle.
Computes PnL%, win/loss classification, and stores performance records.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.signal import Signal
from app.models.trade import Trade
from app.models.signal_performance import SignalPerformance

logger = logging.getLogger(__name__)


class PerformanceTrackerService:
    """Service for tracking trade outcomes and signal performance."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compute_signal_outcome(self, signal_id: int) -> Optional[SignalPerformance]:
        """
        Compute outcome of a signal after trade is closed.
        
        Args:
            signal_id: Signal ID to compute outcome for
            
        Returns:
            SignalPerformance record if trade is closed, None otherwise
        """
        # Get signal with related data
        stmt = select(Signal).where(Signal.id == signal_id).options(
            selectinload(Signal.trades),
            selectinload(Signal.performances)
        )
        result = await self.db.execute(stmt)
        signal = result.scalar_one_or_none()
        
        if not signal:
            logger.warning(f"Signal {signal_id} not found")
            return None
        
        # Check if performance already computed
        if signal.performances:
            logger.info(f"Performance already computed for signal {signal_id}")
            return signal.performances[0]
        
        # Get associated closed trade
        trade = None
        for t in signal.trades:
            if t.status == "closed":
                trade = t
                break
        
        if not trade:
            logger.debug(f"No closed trade found for signal {signal_id}")
            return None
        
        # Compute PnL%
        if trade.trade_type == "BUY":
            # Long trade: profit when exit > entry
            pnl_percent = ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100
        else:
            # Short trade: profit when exit < entry
            pnl_percent = ((trade.entry_price - trade.exit_price) / trade.entry_price) * 100
        
        # Classify outcome
        if pnl_percent > 2:
            outcome = "win"
        elif pnl_percent < -2:
            outcome = "loss"
        else:
            outcome = "breakeven"
        
        # Days held
        days_held = (trade.closed_at - trade.executed_at).days if trade.closed_at else 0
        
        # Create performance record
        performance = SignalPerformance(
            signal_id=signal_id,
            symbol=signal.symbol,
            regime=signal.regime,
            outcome=outcome,
            pnl_percent=pnl_percent,
            days_held=days_held,
            created_at=datetime.utcnow()
        )
        
        self.db.add(performance)
        await self.db.commit()
        await self.db.refresh(performance)
        
        logger.info(f"Computed outcome for signal {signal_id}: {outcome}, PnL={pnl_percent:.2f}%")
        
        return performance
    
    async def compute_all_pending_outcomes(self) -> Dict[str, int]:
        """
        Compute outcomes for all signals with closed trades but no performance record.
        
        Returns:
            Dict with counts: {"processed": N, "computed": M}
        """
        # Find signals with closed trades but no performance record
        stmt = select(Signal).join(Trade).where(
            and_(
                Trade.status == "closed",
                ~Signal.performances.any()
            )
        ).options(
            selectinload(Signal.trades),
            selectinload(Signal.performances)
        )
        
        result = await self.db.execute(stmt)
        pending_signals = result.scalars().unique().all()
        
        processed = 0
        computed = 0
        
        for signal in pending_signals:
            processed += 1
            perf = await self.compute_signal_outcome(signal.id)
            if perf:
                computed += 1
        
        logger.info(f"Processed {processed} pending signals, computed {computed} outcomes")
        
        return {
            "processed": processed,
            "computed": computed
        }
    
    async def mark_expired_signals(self, days_threshold: int = 30) -> int:
        """
        Mark signals as expired if no trade was executed within threshold.
        
        Args:
            days_threshold: Days after which signal is considered expired
            
        Returns:
            Number of signals marked as expired
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Find signals older than threshold with no trades
        stmt = select(Signal).where(
            and_(
                Signal.created_at < cutoff_date,
                ~Signal.trades.any(),
                ~Signal.performances.any()
            )
        )
        
        result = await self.db.execute(stmt)
        expired_signals = result.scalars().all()
        
        count = 0
        for signal in expired_signals:
            # Create performance record with "expired" outcome
            performance = SignalPerformance(
                signal_id=signal.id,
                symbol=signal.symbol,
                regime=signal.regime,
                outcome="expired",
                pnl_percent=0.0,
                days_held=0,
                created_at=datetime.utcnow()
            )
            self.db.add(performance)
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Marked {count} signals as expired")
        
        return count
    
    async def get_signal_performance(self, signal_id: int) -> Optional[SignalPerformance]:
        """
        Get performance record for a signal.
        
        Args:
            signal_id: Signal ID
            
        Returns:
            SignalPerformance record or None
        """
        stmt = select(SignalPerformance).where(SignalPerformance.signal_id == signal_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_recent_performance(self, days: int = 30, limit: int = 100) -> List[SignalPerformance]:
        """
        Get recent signal performance records.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of SignalPerformance records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(SignalPerformance).where(
            SignalPerformance.created_at >= cutoff_date
        ).order_by(
            SignalPerformance.created_at.desc()
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_trade_outcome(self, trade_id: int) -> Optional[SignalPerformance]:
        """
        Update performance record when a trade is closed.
        
        Args:
            trade_id: Trade ID that was just closed
            
        Returns:
            SignalPerformance record if created, None otherwise
        """
        # Get trade with signal
        stmt = select(Trade).where(Trade.id == trade_id).options(
            selectinload(Trade.signal)
        )
        result = await self.db.execute(stmt)
        trade = result.scalar_one_or_none()
        
        if not trade or not trade.signal_id:
            logger.warning(f"Trade {trade_id} not found or has no associated signal")
            return None
        
        if trade.status != "closed":
            logger.warning(f"Trade {trade_id} is not closed yet")
            return None
        
        # Compute outcome for the signal
        return await self.compute_signal_outcome(trade.signal_id)
