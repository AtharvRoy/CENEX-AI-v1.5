"""
Signal Quality Engine (Layer 5)
Filters low-quality signals through multiple quality gates.
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class SignalQualityEngine:
    """
    Signal Quality Engine - Filters signals through quality gates.
    
    Quality checks:
    1. Confidence threshold (regime-aware)
    2. Volatility anomaly detection
    3. Signal decay analysis (recent performance)
    4. Liquidity check
    5. Risk score validation
    """
    
    def __init__(self):
        """Initialize Signal Quality Engine."""
        # Quality gate thresholds (can be tuned)
        self.confidence_thresholds = {
            "high_vol_trending": 0.85,  # Strict (risky regime)
            "low_vol_trending": 0.75,   # Moderate
            "low_vol_ranging": 0.80,    # Moderate-strict (mean reversion)
            "high_vol_ranging": 0.90,   # Very strict (avoid)
            "trending_up": 0.75,
            "trending_down": 0.75,
            "ranging": 0.80,
            "default": 0.80
        }
        
        # Volatility thresholds
        self.vol_spike_multiplier = 3.0  # Flag if current vol > 3x historical
        self.vol_percentile_threshold = 95  # Compare to 95th percentile
        
        # Signal decay thresholds
        self.decay_lookback_signals = 5  # Look at last 5 signals of same type
        self.decay_min_win_rate = 0.4  # Reject if win rate < 40%
        
        # Liquidity thresholds
        self.min_volume_ratio = 0.5  # Current volume must be >= 50% of avg
        self.min_absolute_volume = 100_000  # Minimum 100k shares/units
        
        # Risk thresholds
        self.max_risk_score = 0.3  # Maximum acceptable risk score (0-1 scale)
    
    async def validate(
        self,
        signal: Dict[str, Any],
        symbol: str,
        features: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Run all quality checks on a signal.
        
        Args:
            signal: Signal from Meta Decision Engine
            symbol: Stock symbol
            features: Feature vector (from Layer 2)
            db: Database session
        
        Returns:
            Quality validation result
        """
        try:
            # Initialize results
            checks = {
                "confidence": False,
                "volatility": False,
                "decay": False,
                "liquidity": False,
                "risk": False
            }
            
            details = {}
            
            # Skip checks for NO_SIGNAL
            if signal.get("signal") == "NO_SIGNAL":
                return {
                    "passed": False,
                    "checks": checks,
                    "details": {"reason": "NO_SIGNAL from meta engine"},
                    "final_signal": signal
                }
            
            # Check 1: Confidence threshold (regime-aware)
            confidence_result = self._check_confidence_threshold(signal, features)
            checks["confidence"] = confidence_result["passed"]
            details["confidence"] = confidence_result
            
            # Check 2: Volatility anomaly detection
            volatility_result = self._check_volatility_anomaly(features)
            checks["volatility"] = volatility_result["passed"]
            details["volatility"] = volatility_result
            
            # Check 3: Signal decay analysis (requires DB)
            decay_result = await self._check_signal_decay(signal, symbol, db)
            checks["decay"] = decay_result["passed"]
            details["decay"] = decay_result
            
            # Check 4: Liquidity check
            liquidity_result = self._check_liquidity(features)
            checks["liquidity"] = liquidity_result["passed"]
            details["liquidity"] = liquidity_result
            
            # Check 5: Risk score validation
            risk_result = self._check_risk_score(features)
            checks["risk"] = risk_result["passed"]
            details["risk"] = risk_result
            
            # Final decision: ALL checks must pass
            passed = all(checks.values())
            
            # Prepare final signal
            if passed:
                final_signal = signal
            else:
                # Quality gate failed - downgrade to NO_SIGNAL
                final_signal = {
                    "signal": "NO_SIGNAL",
                    "confidence": 0.0,
                    "reasoning": f"Quality gate failed: {[k for k, v in checks.items() if not v]}",
                    "original_signal": signal
                }
            
            return {
                "passed": passed,
                "checks": checks,
                "details": details,
                "final_signal": final_signal
            }
        
        except Exception as e:
            logger.error(f"Error in signal quality validation: {e}")
            return {
                "passed": False,
                "checks": {},
                "details": {"error": str(e)},
                "final_signal": {
                    "signal": "NO_SIGNAL",
                    "confidence": 0.0,
                    "reasoning": f"Quality engine error: {str(e)}"
                }
            }
    
    def _check_confidence_threshold(
        self,
        signal: Dict[str, Any],
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if signal confidence meets regime-aware threshold.
        
        Args:
            signal: Signal from meta engine
            features: Feature vector
        
        Returns:
            Check result
        """
        try:
            confidence = signal.get("confidence", 0.0)
            
            # Extract regime information
            regime_info = features.get("regime", {})
            regime_label = regime_info.get("regime_label", "default")
            
            # Get appropriate threshold
            required_confidence = self.confidence_thresholds.get(
                regime_label,
                self.confidence_thresholds["default"]
            )
            
            passed = confidence >= required_confidence
            
            return {
                "passed": passed,
                "confidence": confidence,
                "required_confidence": required_confidence,
                "regime": regime_label,
                "message": f"Confidence {confidence:.2f} {'≥' if passed else '<'} threshold {required_confidence:.2f}"
            }
        
        except Exception as e:
            logger.error(f"Error in confidence check: {e}")
            return {
                "passed": False,
                "error": str(e)
            }
    
    def _check_volatility_anomaly(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for extreme volatility spikes.
        
        Args:
            features: Feature vector
        
        Returns:
            Check result
        """
        try:
            technical = features.get("technical", {})
            
            # Get current and historical volatility
            current_atr = technical.get("atr_14", 0.0)
            historical_vol = technical.get("hist_vol_20d", 0.0)
            
            # Get volatility percentile from regime
            regime_info = features.get("regime", {})
            vol_percentile = regime_info.get("volatility_percentile", 50)
            
            # Check 1: Current ATR vs historical volatility
            if historical_vol > 0:
                vol_ratio = current_atr / historical_vol
            else:
                vol_ratio = 1.0
            
            # Check 2: Volatility percentile
            extreme_vol = vol_percentile > self.vol_percentile_threshold
            vol_spike = vol_ratio > self.vol_spike_multiplier
            
            passed = not (extreme_vol or vol_spike)
            
            return {
                "passed": passed,
                "current_atr": current_atr,
                "historical_vol": historical_vol,
                "vol_ratio": vol_ratio,
                "vol_percentile": vol_percentile,
                "extreme_vol": extreme_vol,
                "vol_spike": vol_spike,
                "message": f"Volatility check: {'PASS' if passed else 'FAIL'} (ratio={vol_ratio:.2f}, percentile={vol_percentile})"
            }
        
        except Exception as e:
            logger.error(f"Error in volatility check: {e}")
            return {
                "passed": True,  # Default to pass on error (non-critical)
                "error": str(e)
            }
    
    async def _check_signal_decay(
        self,
        signal: Dict[str, Any],
        symbol: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Check if similar signals have been failing recently.
        
        Args:
            signal: Signal from meta engine
            symbol: Stock symbol
            db: Database session
        
        Returns:
            Check result
        """
        try:
            signal_type = signal.get("signal")
            
            # Query recent signals of same type for this symbol
            query = select(Signal).where(
                and_(
                    Signal.symbol == symbol,
                    Signal.signal_type == signal_type
                )
            ).order_by(desc(Signal.created_at)).limit(self.decay_lookback_signals)
            
            result = await db.execute(query)
            recent_signals = result.scalars().all()
            
            if len(recent_signals) == 0:
                # No historical data - pass by default
                return {
                    "passed": True,
                    "recent_signals_count": 0,
                    "message": "No recent signal history - default pass"
                }
            
            # Calculate win rate from performances
            # Note: This requires signal_performance table to be populated
            # For now, we'll estimate based on signal confidence
            # TODO: Link to actual trade outcomes when performance tracking is built
            
            wins = 0
            total = 0
            
            for hist_signal in recent_signals:
                if hist_signal.performances:
                    # If performance data exists, use it
                    for perf in hist_signal.performances:
                        if hasattr(perf, 'outcome'):
                            total += 1
                            if perf.outcome == 'win':
                                wins += 1
                else:
                    # No performance data - assume win if confidence was high
                    total += 1
                    if hist_signal.confidence >= 0.7:
                        wins += 1
            
            if total > 0:
                win_rate = wins / total
            else:
                win_rate = 0.5  # Neutral assumption
            
            passed = win_rate >= self.decay_min_win_rate
            
            return {
                "passed": passed,
                "recent_signals_count": len(recent_signals),
                "wins": wins,
                "total": total,
                "win_rate": win_rate,
                "required_win_rate": self.decay_min_win_rate,
                "message": f"Signal decay check: {'PASS' if passed else 'FAIL'} (win_rate={win_rate:.2%})"
            }
        
        except Exception as e:
            logger.error(f"Error in signal decay check: {e}")
            return {
                "passed": True,  # Default to pass on error
                "error": str(e)
            }
    
    def _check_liquidity(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if symbol has sufficient trading volume.
        
        Args:
            features: Feature vector
        
        Returns:
            Check result
        """
        try:
            price_info = features.get("price", {})
            technical = features.get("technical", {})
            
            # Get volume data
            current_volume = price_info.get("volume", 0)
            avg_volume = technical.get("volume_sma_20", 0)
            
            # Check 1: Volume ratio (current vs average)
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume
            else:
                volume_ratio = 1.0
            
            ratio_check = volume_ratio >= self.min_volume_ratio
            
            # Check 2: Absolute volume
            absolute_check = current_volume >= self.min_absolute_volume
            
            passed = ratio_check and absolute_check
            
            return {
                "passed": passed,
                "current_volume": current_volume,
                "avg_volume": avg_volume,
                "volume_ratio": volume_ratio,
                "min_ratio": self.min_volume_ratio,
                "min_absolute": self.min_absolute_volume,
                "ratio_check": ratio_check,
                "absolute_check": absolute_check,
                "message": f"Liquidity check: {'PASS' if passed else 'FAIL'} (ratio={volume_ratio:.2f}, volume={current_volume:,.0f})"
            }
        
        except Exception as e:
            logger.error(f"Error in liquidity check: {e}")
            return {
                "passed": True,  # Default to pass on error (non-critical)
                "error": str(e)
            }
    
    def _check_risk_score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate risk score is within acceptable range.
        
        Args:
            features: Feature vector
        
        Returns:
            Check result
        """
        try:
            # Extract risk-related metrics
            technical = features.get("technical", {})
            regime_info = features.get("regime", {})
            
            # Calculate composite risk score
            # Higher volatility = higher risk
            atr_pct = technical.get("atr_pct", 0.0)
            vol_percentile = regime_info.get("volatility_percentile", 50) / 100.0
            
            # Normalize ATR percentage (assume 0-10% range)
            normalized_atr = min(atr_pct / 10.0, 1.0)
            
            # Composite risk score (0-1 scale)
            risk_score = (normalized_atr * 0.6 + vol_percentile * 0.4)
            
            passed = risk_score <= self.max_risk_score
            
            return {
                "passed": passed,
                "risk_score": risk_score,
                "max_risk_score": self.max_risk_score,
                "atr_pct": atr_pct,
                "vol_percentile": vol_percentile * 100,
                "message": f"Risk check: {'PASS' if passed else 'FAIL'} (score={risk_score:.2f}, max={self.max_risk_score:.2f})"
            }
        
        except Exception as e:
            logger.error(f"Error in risk check: {e}")
            return {
                "passed": True,  # Default to pass on error
                "error": str(e)
            }
    
    def update_thresholds(self, thresholds: Dict[str, Any]):
        """
        Update quality gate thresholds dynamically.
        
        Args:
            thresholds: Dictionary of threshold updates
        """
        if "confidence_thresholds" in thresholds:
            self.confidence_thresholds.update(thresholds["confidence_thresholds"])
        
        if "vol_spike_multiplier" in thresholds:
            self.vol_spike_multiplier = thresholds["vol_spike_multiplier"]
        
        if "decay_min_win_rate" in thresholds:
            self.decay_min_win_rate = thresholds["decay_min_win_rate"]
        
        if "min_volume_ratio" in thresholds:
            self.min_volume_ratio = thresholds["min_volume_ratio"]
        
        if "max_risk_score" in thresholds:
            self.max_risk_score = thresholds["max_risk_score"]
        
        logger.info("Quality gate thresholds updated")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current quality gate configuration."""
        return {
            "confidence_thresholds": self.confidence_thresholds,
            "vol_spike_multiplier": self.vol_spike_multiplier,
            "vol_percentile_threshold": self.vol_percentile_threshold,
            "decay_lookback_signals": self.decay_lookback_signals,
            "decay_min_win_rate": self.decay_min_win_rate,
            "min_volume_ratio": self.min_volume_ratio,
            "min_absolute_volume": self.min_absolute_volume,
            "max_risk_score": self.max_risk_score
        }


# Singleton instance
signal_quality_engine = SignalQualityEngine()
