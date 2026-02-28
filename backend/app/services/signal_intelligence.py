"""
Signal Intelligence Service (Layer 6 - Performance Memory)

Aggregates performance data to build "signal memory".
Learns which signals work in which regimes for adaptive signal generation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.signal import Signal
from app.models.signal_performance import SignalPerformance

logger = logging.getLogger(__name__)


class SignalIntelligenceService:
    """Service for building signal memory and adaptive intelligence."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_symbol_intelligence(self, symbol: str, days: int = 90) -> Dict[str, Any]:
        """
        Get comprehensive intelligence for a specific symbol.
        
        Args:
            symbol: Stock symbol
            days: Lookback period
            
        Returns:
            Dict with symbol-specific intelligence
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get all signals and performances for this symbol
        query = select(Signal).where(
            and_(
                Signal.symbol == symbol,
                Signal.created_at >= cutoff
            )
        ).options(selectinload(Signal.performances))
        
        result = await self.db.execute(query)
        signals = result.scalars().all()
        
        if not signals:
            return {
                "symbol": symbol,
                "intelligence": "insufficient_data",
                "sample_size": 0
            }
        
        # Separate signals with and without outcomes
        with_outcomes = [s for s in signals if s.performances]
        without_outcomes = [s for s in signals if not s.performances]
        
        # Analyze by signal type
        by_signal_type = self._analyze_by_dimension(
            with_outcomes,
            lambda s: s.signal_type
        )
        
        # Analyze by regime
        by_regime = self._analyze_by_dimension(
            with_outcomes,
            lambda s: s.regime or "unknown"
        )
        
        # Analyze by confidence level
        by_confidence = self._analyze_by_confidence_buckets(with_outcomes)
        
        # Feature importance (if available in reasoning)
        feature_insights = self._extract_feature_insights(with_outcomes)
        
        # Best performing configurations
        best_config = self._find_best_configuration(with_outcomes)
        
        return {
            "symbol": symbol,
            "total_signals": len(signals),
            "signals_with_outcomes": len(with_outcomes),
            "signals_pending": len(without_outcomes),
            "by_signal_type": by_signal_type,
            "by_regime": by_regime,
            "by_confidence": by_confidence,
            "feature_insights": feature_insights,
            "best_configuration": best_config,
            "lookback_days": days
        }
    
    async def get_regime_intelligence(self, regime: str, days: int = 90) -> Dict[str, Any]:
        """
        Get intelligence for a specific market regime.
        
        Args:
            regime: Market regime (e.g., "high_vol_trending")
            days: Lookback period
            
        Returns:
            Dict with regime-specific intelligence
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(Signal).where(
            and_(
                Signal.regime == regime,
                Signal.created_at >= cutoff
            )
        ).options(selectinload(Signal.performances))
        
        result = await self.db.execute(query)
        signals = result.scalars().all()
        
        with_outcomes = [s for s in signals if s.performances]
        
        if not with_outcomes:
            return {
                "regime": regime,
                "intelligence": "insufficient_data",
                "sample_size": 0
            }
        
        # Analyze what works in this regime
        by_signal_type = self._analyze_by_dimension(
            with_outcomes,
            lambda s: s.signal_type
        )
        
        by_symbol = self._analyze_by_dimension(
            with_outcomes,
            lambda s: s.symbol
        )
        
        # Adaptive thresholds for this regime
        adaptive_thresholds = self._compute_adaptive_thresholds(with_outcomes)
        
        return {
            "regime": regime,
            "total_signals": len(with_outcomes),
            "by_signal_type": by_signal_type,
            "top_symbols": self._get_top_performers(by_symbol, top_n=10),
            "adaptive_thresholds": adaptive_thresholds,
            "lookback_days": days
        }
    
    async def get_agent_intelligence(self, days: int = 90) -> Dict[str, Dict[str, Any]]:
        """
        Get intelligence on which agents perform best in which conditions.
        
        Args:
            days: Lookback period
            
        Returns:
            Dict mapping agent -> intelligence
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(Signal).join(SignalPerformance).where(
            SignalPerformance.created_at >= cutoff
        ).options(selectinload(Signal.performances))
        
        result = await self.db.execute(query)
        signals = result.scalars().unique().all()
        
        # Track agent performance by regime
        agent_by_regime: Dict[str, Dict[str, List[Tuple[str, str]]]] = {
            "quant": {},
            "sentiment": {},
            "regime": {}
        }
        
        for signal in signals:
            if not signal.performances or not signal.reasoning:
                continue
            
            performance = signal.performances[0]
            agent_outputs = signal.reasoning.get("agent_outputs", {})
            regime = signal.regime or "unknown"
            
            for agent_name in ["quant", "sentiment", "regime"]:
                if agent_name not in agent_outputs:
                    continue
                
                if regime not in agent_by_regime[agent_name]:
                    agent_by_regime[agent_name][regime] = []
                
                agent_signal = agent_outputs[agent_name].get("signal", "HOLD")
                outcome = performance.outcome
                
                agent_by_regime[agent_name][regime].append((agent_signal, outcome))
        
        # Compute accuracy by regime for each agent
        intelligence = {}
        for agent_name, regimes in agent_by_regime.items():
            intelligence[agent_name] = {
                "overall_accuracy": 0.0,
                "by_regime": {},
                "best_regime": None,
                "worst_regime": None
            }
            
            regime_accuracies = {}
            for regime, predictions in regimes.items():
                if not predictions:
                    continue
                
                correct = sum(
                    1 for signal, outcome in predictions
                    if (signal in ["BUY", "STRONG_BUY"] and outcome == "win") or
                       (signal in ["SELL", "STRONG_SELL"] and outcome == "win") or
                       (signal == "HOLD" and outcome in ["breakeven", "expired"])
                )
                
                accuracy = correct / len(predictions)
                regime_accuracies[regime] = accuracy
                
                intelligence[agent_name]["by_regime"][regime] = {
                    "accuracy": float(accuracy),
                    "sample_size": len(predictions)
                }
            
            if regime_accuracies:
                intelligence[agent_name]["overall_accuracy"] = float(np.mean(list(regime_accuracies.values())))
                intelligence[agent_name]["best_regime"] = max(regime_accuracies, key=regime_accuracies.get)
                intelligence[agent_name]["worst_regime"] = min(regime_accuracies, key=regime_accuracies.get)
        
        return intelligence
    
    async def recommend_signal_adjustments(self, symbol: str) -> Dict[str, Any]:
        """
        Recommend adjustments to signal generation for a symbol based on performance.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with recommendations
        """
        # Get recent intelligence
        intelligence = await self.get_symbol_intelligence(symbol, days=60)
        
        if intelligence.get("intelligence") == "insufficient_data":
            return {
                "symbol": symbol,
                "recommendations": [],
                "reason": "insufficient_data"
            }
        
        recommendations = []
        
        # Check overall performance
        by_signal_type = intelligence.get("by_signal_type", {})
        
        for signal_type, metrics in by_signal_type.items():
            win_rate = metrics.get("win_rate", 0.0)
            count = metrics.get("count", 0)
            
            if count >= 10:  # Enough data
                if win_rate < 0.45:
                    recommendations.append({
                        "type": "reduce_signal_type",
                        "signal_type": signal_type,
                        "reason": f"Low win rate ({win_rate:.1%})",
                        "action": "decrease_confidence_threshold"
                    })
                elif win_rate > 0.70:
                    recommendations.append({
                        "type": "increase_signal_type",
                        "signal_type": signal_type,
                        "reason": f"High win rate ({win_rate:.1%})",
                        "action": "increase_signal_frequency"
                    })
        
        # Check regime-specific performance
        by_regime = intelligence.get("by_regime", {})
        
        for regime, metrics in by_regime.items():
            win_rate = metrics.get("win_rate", 0.0)
            count = metrics.get("count", 0)
            
            if count >= 5 and win_rate < 0.40:
                recommendations.append({
                    "type": "avoid_regime",
                    "regime": regime,
                    "reason": f"Poor performance in {regime} ({win_rate:.1%})",
                    "action": "pause_signals_in_regime"
                })
        
        # Check confidence calibration
        by_confidence = intelligence.get("by_confidence", {})
        
        for bucket, metrics in by_confidence.items():
            if metrics.get("count", 0) >= 5:
                win_rate = metrics.get("win_rate", 0.0)
                
                if bucket == "high" and win_rate < 0.60:
                    recommendations.append({
                        "type": "recalibrate_confidence",
                        "bucket": bucket,
                        "reason": "High confidence signals underperforming",
                        "action": "increase_confidence_threshold"
                    })
        
        return {
            "symbol": symbol,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations)
        }
    
    def _analyze_by_dimension(
        self, 
        signals: List[Signal], 
        dimension_fn: callable
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze signals grouped by a dimension (signal_type, regime, etc.).
        
        Args:
            signals: List of signals with performances
            dimension_fn: Function to extract dimension value from signal
            
        Returns:
            Dict mapping dimension_value -> metrics
        """
        grouped: Dict[str, List[SignalPerformance]] = {}
        
        for signal in signals:
            if not signal.performances:
                continue
            
            dimension_value = dimension_fn(signal)
            if dimension_value not in grouped:
                grouped[dimension_value] = []
            
            grouped[dimension_value].append(signal.performances[0])
        
        # Compute metrics
        metrics = {}
        for dimension_value, perfs in grouped.items():
            wins = sum(1 for p in perfs if p.outcome == "win")
            total = len(perfs)
            pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
            
            metrics[dimension_value] = {
                "count": total,
                "win_rate": wins / total if total > 0 else 0.0,
                "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0,
                "total_pnl": float(sum(pnl_values)) if pnl_values else 0.0
            }
        
        return metrics
    
    def _analyze_by_confidence_buckets(self, signals: List[Signal]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze signals grouped by confidence level buckets.
        
        Args:
            signals: List of signals with performances
            
        Returns:
            Dict mapping bucket -> metrics
        """
        buckets = {
            "high": [],  # >= 0.75
            "medium": [],  # 0.50 - 0.75
            "low": []  # < 0.50
        }
        
        for signal in signals:
            if not signal.performances:
                continue
            
            if signal.confidence >= 0.75:
                bucket = "high"
            elif signal.confidence >= 0.50:
                bucket = "medium"
            else:
                bucket = "low"
            
            buckets[bucket].append(signal.performances[0])
        
        # Compute metrics
        metrics = {}
        for bucket, perfs in buckets.items():
            if not perfs:
                continue
            
            wins = sum(1 for p in perfs if p.outcome == "win")
            total = len(perfs)
            pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
            
            metrics[bucket] = {
                "count": total,
                "win_rate": wins / total if total > 0 else 0.0,
                "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0
            }
        
        return metrics
    
    def _extract_feature_insights(self, signals: List[Signal]) -> Dict[str, Any]:
        """
        Extract insights on which features are most predictive.
        
        Args:
            signals: List of signals with performances
            
        Returns:
            Dict with feature insights
        """
        # This would analyze feature_importance from reasoning
        # For now, return placeholder
        return {
            "available": False,
            "note": "Feature importance tracking requires agent feature exports"
        }
    
    def _find_best_configuration(self, signals: List[Signal]) -> Optional[Dict[str, Any]]:
        """
        Find the best performing signal configuration.
        
        Args:
            signals: List of signals with performances
            
        Returns:
            Dict with best configuration or None
        """
        if not signals:
            return None
        
        # Group by (signal_type, regime)
        configs: Dict[Tuple[str, str], List[SignalPerformance]] = {}
        
        for signal in signals:
            if not signal.performances:
                continue
            
            config_key = (signal.signal_type, signal.regime or "unknown")
            if config_key not in configs:
                configs[config_key] = []
            
            configs[config_key].append(signal.performances[0])
        
        # Find best config (highest win rate with at least 5 samples)
        best_config = None
        best_win_rate = 0.0
        
        for (signal_type, regime), perfs in configs.items():
            if len(perfs) < 5:
                continue
            
            wins = sum(1 for p in perfs if p.outcome == "win")
            win_rate = wins / len(perfs)
            
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                pnl_values = [p.pnl_percent for p in perfs if p.pnl_percent is not None]
                
                best_config = {
                    "signal_type": signal_type,
                    "regime": regime,
                    "win_rate": float(win_rate),
                    "avg_pnl": float(np.mean(pnl_values)) if pnl_values else 0.0,
                    "sample_size": len(perfs)
                }
        
        return best_config
    
    def _compute_adaptive_thresholds(self, signals: List[Signal]) -> Dict[str, float]:
        """
        Compute adaptive confidence thresholds based on regime performance.
        
        Args:
            signals: List of signals with performances
            
        Returns:
            Dict with recommended thresholds
        """
        if not signals:
            return {"min_confidence": 0.5}
        
        # Analyze confidence vs win rate
        confidence_performance = []
        
        for signal in signals:
            if not signal.performances:
                continue
            
            perf = signal.performances[0]
            is_win = perf.outcome == "win"
            
            confidence_performance.append({
                "confidence": signal.confidence,
                "is_win": is_win
            })
        
        # Find minimum confidence where win rate >= 55%
        confidence_performance.sort(key=lambda x: x["confidence"])
        
        min_confidence = 0.5
        for i in range(len(confidence_performance)):
            subset = confidence_performance[i:]
            if len(subset) >= 10:
                win_rate = sum(1 for x in subset if x["is_win"]) / len(subset)
                if win_rate >= 0.55:
                    min_confidence = confidence_performance[i]["confidence"]
                    break
        
        return {
            "min_confidence": float(min_confidence),
            "recommended_threshold": float(max(0.5, min_confidence))
        }
    
    def _get_top_performers(self, metrics: Dict[str, Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get top N performers from metrics dict.
        
        Args:
            metrics: Dict mapping key -> metrics
            top_n: Number of top performers to return
            
        Returns:
            List of top performers
        """
        items = []
        for key, m in metrics.items():
            if m.get("count", 0) >= 3:  # Minimum sample size
                items.append({
                    "key": key,
                    **m
                })
        
        # Sort by win rate, then avg PnL
        items.sort(key=lambda x: (x.get("win_rate", 0), x.get("avg_pnl", 0)), reverse=True)
        
        return items[:top_n]
