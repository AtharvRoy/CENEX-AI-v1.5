"""
Performance Analytics Service (Layer 6 - Performance Memory)

Computes win rates, agent accuracy, regime-specific performance.
Detects signal decay and provides insights for self-learning.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.signal import Signal
from app.models.signal_performance import SignalPerformance

logger = logging.getLogger(__name__)


class PerformanceAnalyticsService:
    """Service for analyzing signal and agent performance."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_overall_metrics(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get overall system performance metrics.
        
        Args:
            days: Number of days to look back (None = all time)
            
        Returns:
            Dict with overall performance metrics
        """
        query = select(SignalPerformance)
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(SignalPerformance.created_at >= cutoff)
        
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        if not performances:
            return {
                "total_signals": 0,
                "win_rate": 0.0,
                "avg_pnl_percent": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "avg_days_held": 0.0,
                "by_outcome": {}
            }
        
        # Basic counts
        total = len(performances)
        wins = sum(1 for p in performances if p.outcome == "win")
        losses = sum(1 for p in performances if p.outcome == "loss")
        breakeven = sum(1 for p in performances if p.outcome == "breakeven")
        expired = sum(1 for p in performances if p.outcome == "expired")
        
        # PnL metrics
        pnl_values = [p.pnl_percent for p in performances if p.pnl_percent is not None]
        avg_pnl = np.mean(pnl_values) if pnl_values else 0.0
        total_pnl = sum(pnl_values) if pnl_values else 0.0
        
        # Sharpe ratio (annualized)
        sharpe = 0.0
        if pnl_values and len(pnl_values) > 1:
            std_pnl = np.std(pnl_values)
            if std_pnl > 0:
                # Annualize: assuming ~250 trading days
                sharpe = (avg_pnl / std_pnl) * np.sqrt(250)
        
        # Max drawdown
        max_dd = self._compute_max_drawdown(pnl_values) if pnl_values else 0.0
        
        # Average days held
        days_held_values = [p.days_held for p in performances if p.days_held is not None]
        avg_days = np.mean(days_held_values) if days_held_values else 0.0
        
        return {
            "total_signals": total,
            "win_rate": wins / total if total > 0 else 0.0,
            "avg_pnl_percent": float(avg_pnl),
            "total_pnl": float(total_pnl),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_dd),
            "avg_days_held": float(avg_days),
            "by_outcome": {
                "win": wins,
                "loss": losses,
                "breakeven": breakeven,
                "expired": expired
            }
        }
    
    async def get_performance_by_signal_type(self, days: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics grouped by signal type.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict mapping signal_type -> metrics
        """
        # Get signals with performances
        query = select(Signal).join(SignalPerformance).options(
            selectinload(Signal.performances)
        )
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(SignalPerformance.created_at >= cutoff)
        
        result = await self.db.execute(query)
        signals = result.scalars().unique().all()
        
        # Group by signal type
        by_type: Dict[str, List[SignalPerformance]] = {}
        for signal in signals:
            if signal.performances:
                perf = signal.performances[0]
                if signal.signal_type not in by_type:
                    by_type[signal.signal_type] = []
                by_type[signal.signal_type].append(perf)
        
        # Compute metrics for each type
        metrics = {}
        for signal_type, perfs in by_type.items():
            wins = sum(1 for p in perfs if p.outcome == "win")
            total = len(perfs)
            pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
            
            metrics[signal_type] = {
                "count": total,
                "win_rate": wins / total if total > 0 else 0.0,
                "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0,
                "total_pnl": float(sum(pnl_values)) if pnl_values else 0.0
            }
        
        return metrics
    
    async def get_performance_by_regime(self, days: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics grouped by regime.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict mapping regime -> metrics
        """
        query = select(SignalPerformance)
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(SignalPerformance.created_at >= cutoff)
        
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        # Group by regime
        by_regime: Dict[str, List[SignalPerformance]] = {}
        for perf in performances:
            regime = perf.regime or "unknown"
            if regime not in by_regime:
                by_regime[regime] = []
            by_regime[regime].append(perf)
        
        # Compute metrics for each regime
        metrics = {}
        for regime, perfs in by_regime.items():
            wins = sum(1 for p in perfs if p.outcome == "win")
            total = len(perfs)
            pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
            
            metrics[regime] = {
                "count": total,
                "win_rate": wins / total if total > 0 else 0.0,
                "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0,
                "total_pnl": float(sum(pnl_values)) if pnl_values else 0.0
            }
        
        return metrics
    
    async def get_performance_by_symbol(self, days: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics grouped by symbol.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict mapping symbol -> metrics
        """
        query = select(SignalPerformance)
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(SignalPerformance.created_at >= cutoff)
        
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        # Group by symbol
        by_symbol: Dict[str, List[SignalPerformance]] = {}
        for perf in performances:
            if perf.symbol not in by_symbol:
                by_symbol[perf.symbol] = []
            by_symbol[perf.symbol].append(perf)
        
        # Compute metrics for each symbol
        metrics = {}
        for symbol, perfs in by_symbol.items():
            wins = sum(1 for p in perfs if p.outcome == "win")
            total = len(perfs)
            pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
            
            metrics[symbol] = {
                "count": total,
                "win_rate": wins / total if total > 0 else 0.0,
                "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0,
                "total_pnl": float(sum(pnl_values)) if pnl_values else 0.0
            }
        
        return metrics
    
    async def analyze_agent_performance(self, days: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Analyze which agent is most accurate by checking agent outputs in reasoning.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict mapping agent_name -> accuracy metrics
        """
        # Get signals with performances and reasoning
        query = select(Signal).join(SignalPerformance).options(
            selectinload(Signal.performances)
        )
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(SignalPerformance.created_at >= cutoff)
        
        result = await self.db.execute(query)
        signals = result.scalars().unique().all()
        
        # Track agent predictions vs outcomes
        agent_stats = {
            "quant": {"correct": 0, "total": 0},
            "sentiment": {"correct": 0, "total": 0},
            "regime": {"correct": 0, "total": 0},
        }
        
        for signal in signals:
            if not signal.performances or not signal.reasoning:
                continue
            
            performance = signal.performances[0]
            agent_outputs = signal.reasoning.get("agent_outputs", {})
            
            # Check each agent's prediction
            for agent_name in ["quant", "sentiment", "regime"]:
                if agent_name not in agent_outputs:
                    continue
                
                agent_output = agent_outputs[agent_name]
                agent_signal = agent_output.get("signal", "HOLD")
                
                agent_stats[agent_name]["total"] += 1
                
                # Agent is "correct" if:
                # - Predicted BUY/STRONG_BUY and outcome was win
                # - Predicted SELL/STRONG_SELL and outcome was win (short)
                # - Predicted HOLD and outcome was breakeven/expired
                is_bullish = agent_signal in ["BUY", "STRONG_BUY"]
                is_bearish = agent_signal in ["SELL", "STRONG_SELL"]
                is_neutral = agent_signal == "HOLD"
                
                if (is_bullish and performance.outcome == "win") or \
                   (is_bearish and performance.outcome == "win") or \
                   (is_neutral and performance.outcome in ["breakeven", "expired"]):
                    agent_stats[agent_name]["correct"] += 1
        
        # Compute accuracy
        metrics = {}
        for agent_name, stats in agent_stats.items():
            total = stats["total"]
            accuracy = stats["correct"] / total if total > 0 else 0.0
            
            metrics[agent_name] = {
                "accuracy": float(accuracy),
                "total_predictions": total,
                "correct_predictions": stats["correct"]
            }
        
        return metrics
    
    async def detect_signal_decay(
        self, 
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect if signal quality is degrading over time.
        
        Args:
            symbol: Filter by symbol (optional)
            signal_type: Filter by signal type (optional)
            lookback_days: Days to analyze
            
        Returns:
            Dict with decay analysis
        """
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Build query
        query = select(Signal).join(SignalPerformance).where(
            SignalPerformance.created_at >= cutoff
        ).options(selectinload(Signal.performances))
        
        if symbol:
            query = query.where(Signal.symbol == symbol)
        if signal_type:
            query = query.where(Signal.signal_type == signal_type)
        
        result = await self.db.execute(query)
        signals = result.scalars().unique().all()
        
        if len(signals) < 10:
            return {
                "decaying": False,
                "reason": "insufficient_data",
                "sample_size": len(signals)
            }
        
        # Extract performance data
        performances = [s.performances[0] for s in signals if s.performances]
        wins = sum(1 for p in performances if p.outcome == "win")
        win_rate = wins / len(performances) if performances else 0.0
        
        pnl_values = [p.pnl_percent for p in performances if p.pnl_percent is not None]
        avg_pnl = np.mean(pnl_values) if pnl_values else 0.0
        
        # Check for decay
        is_decaying = win_rate < 0.5 or avg_pnl < 0
        
        return {
            "decaying": is_decaying,
            "win_rate": float(win_rate),
            "avg_pnl": float(avg_pnl),
            "sample_size": len(signals),
            "lookback_days": lookback_days,
            "recommendation": "reduce_confidence_or_pause" if is_decaying else "continue"
        }
    
    def _compute_max_drawdown(self, pnl_values: List[float]) -> float:
        """
        Compute maximum drawdown from PnL series.
        
        Args:
            pnl_values: List of PnL percentages
            
        Returns:
            Max drawdown as decimal (e.g., 0.15 = 15%)
        """
        if not pnl_values:
            return 0.0
        
        # Compute cumulative returns
        cumulative = np.cumsum(pnl_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / 100.0  # Convert to decimal
        
        max_dd = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        return float(max_dd)
    
    async def get_performance_trend(self, days: int = 90, window_days: int = 30) -> List[Dict[str, Any]]:
        """
        Get performance trend over time using rolling windows.
        
        Args:
            days: Total days to analyze
            window_days: Rolling window size
            
        Returns:
            List of metrics for each window
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(SignalPerformance).where(
            SignalPerformance.created_at >= cutoff
        ).order_by(SignalPerformance.created_at)
        
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        if not performances:
            return []
        
        # Group into time windows
        trends = []
        current_date = cutoff
        end_date = datetime.utcnow()
        
        while current_date < end_date:
            window_end = current_date + timedelta(days=window_days)
            
            # Get performances in this window
            window_perfs = [
                p for p in performances 
                if current_date <= p.created_at < window_end
            ]
            
            if window_perfs:
                wins = sum(1 for p in window_perfs if p.outcome == "win")
                total = len(window_perfs)
                pnl_values = [p.pnl_percent for p in window_perfs if p.pnl_percent is not None]
                
                trends.append({
                    "start_date": current_date.isoformat(),
                    "end_date": window_end.isoformat(),
                    "count": total,
                    "win_rate": wins / total if total > 0 else 0.0,
                    "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0
                })
            
            current_date = window_end
        
        return trends
