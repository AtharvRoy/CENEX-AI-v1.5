"""
Regime Agent
Market regime-based strategy selection.
"""

import logging
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent, AgentOutput, SignalType

logger = logging.getLogger(__name__)


class RegimeAgent(BaseAgent):
    """
    Regime-based strategy agent.
    
    Strategies:
    - High-vol trending → Trend-following (MACD, ADX)
    - Low-vol ranging → Mean reversion (RSI, Bollinger)
    - High-vol ranging → Avoid trading (NO_SIGNAL)
    - Low-vol trending → Momentum breakout
    """
    
    def __init__(self):
        """Initialize Regime Agent."""
        super().__init__(name="regime", version="1.0")
    
    def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Regime agent uses rule-based strategies, no model to load.
        
        Args:
            model_path: Not used
        """
        logger.info("Regime agent uses rule-based strategies, no model loading required")
    
    async def analyze(
        self, 
        symbol: str, 
        features: Dict[str, Any],
        **kwargs
    ) -> AgentOutput:
        """
        Analyze symbol based on market regime.
        
        Args:
            symbol: Stock symbol
            features: Feature vector dictionary
            **kwargs: Additional parameters
        
        Returns:
            AgentOutput with regime-specific signal
        """
        # Validate features
        if not self._validate_features(features, ['regime', 'technical']):
            return self._no_signal_output(symbol, "Missing regime or technical data")
        
        regime_data = features.get('regime', {})
        technical = features.get('technical', {})
        
        return await self._regime_strategy(symbol, regime_data, technical)
    
    async def _regime_strategy(
        self, 
        symbol: str, 
        regime_data: Dict[str, Any], 
        technical: Dict[str, Any]
    ) -> AgentOutput:
        """
        Apply regime-specific trading strategy.
        
        Args:
            symbol: Stock symbol
            regime_data: Regime classification data
            technical: Technical indicators
        
        Returns:
            AgentOutput
        """
        try:
            # Extract regime information
            combined_regime = regime_data.get('combined', 'unknown')
            volatility = regime_data.get('volatility', 'unknown')
            trend = regime_data.get('trend', 'unknown')
            confidence = regime_data.get('confidence', 0.5)
            
            # Extract technical indicators
            rsi = technical.get('rsi_14')
            macd_hist = technical.get('macd_hist')
            adx = technical.get('adx_14')
            bb_position = technical.get('bb_position')
            
            # Route to appropriate strategy based on regime
            if combined_regime == 'high_vol_trending':
                return self._trend_following_strategy(
                    symbol, combined_regime, macd_hist, adx, confidence
                )
            elif combined_regime == 'low_vol_ranging':
                return self._mean_reversion_strategy(
                    symbol, combined_regime, rsi, bb_position, confidence
                )
            elif combined_regime == 'high_vol_ranging':
                return self._avoid_strategy(symbol, combined_regime, confidence)
            elif combined_regime == 'low_vol_trending':
                return self._momentum_breakout_strategy(
                    symbol, combined_regime, rsi, macd_hist, adx, confidence
                )
            else:
                # Unknown regime
                return self._no_signal_output(symbol, f"Unknown regime: {combined_regime}")
        
        except Exception as e:
            logger.error(f"Error in regime strategy for {symbol}: {e}")
            return self._no_signal_output(symbol, f"Strategy error: {str(e)}")
    
    def _trend_following_strategy(
        self, 
        symbol: str, 
        regime: str, 
        macd_hist: Optional[float], 
        adx: Optional[float],
        base_confidence: float
    ) -> AgentOutput:
        """
        Trend-following strategy for high-vol trending regime.
        
        Args:
            symbol: Stock symbol
            regime: Regime name
            macd_hist: MACD histogram
            adx: ADX indicator
            base_confidence: Base confidence from regime detection
        
        Returns:
            AgentOutput
        """
        if macd_hist is None or adx is None:
            return self._no_signal_output(symbol, "Missing indicators for trend-following")
        
        # Strong trend + positive MACD → BUY
        # Strong trend + negative MACD → SELL
        
        if adx > 30:  # Strong trend
            if macd_hist > 5:
                signal = SignalType.BUY
                confidence = min(base_confidence + 0.2, 0.9)
                rationale = "Strong uptrend confirmed by MACD and ADX"
            elif macd_hist < -5:
                signal = SignalType.SELL
                confidence = min(base_confidence + 0.2, 0.9)
                rationale = "Strong downtrend confirmed by MACD and ADX"
            elif macd_hist > 0:
                signal = SignalType.BUY
                confidence = base_confidence
                rationale = "Uptrend with moderate MACD signal"
            else:
                signal = SignalType.SELL
                confidence = base_confidence
                rationale = "Downtrend with moderate MACD signal"
        else:  # Weak trend
            signal = SignalType.HOLD
            confidence = 0.5
            rationale = "Trend not strong enough for entry"
        
        reasoning = {
            "model_version": self.version,
            "strategy": "trend_following",
            "regime": regime,
            "macd_hist": macd_hist,
            "adx": adx,
            "rationale": rationale
        }
        
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _mean_reversion_strategy(
        self, 
        symbol: str, 
        regime: str, 
        rsi: Optional[float], 
        bb_position: Optional[float],
        base_confidence: float
    ) -> AgentOutput:
        """
        Mean reversion strategy for low-vol ranging regime.
        
        Args:
            symbol: Stock symbol
            regime: Regime name
            rsi: RSI indicator
            bb_position: Bollinger Band position
            base_confidence: Base confidence from regime detection
        
        Returns:
            AgentOutput
        """
        if rsi is None:
            return self._no_signal_output(symbol, "Missing RSI for mean reversion")
        
        # Buy oversold, sell overbought
        if rsi < 30:
            signal = SignalType.BUY
            confidence = min(base_confidence + 0.15, 0.85)
            rationale = "Oversold condition in ranging market - mean reversion opportunity"
        elif rsi < 40 and bb_position is not None and bb_position < 0.3:
            signal = SignalType.BUY
            confidence = base_confidence
            rationale = "Near lower Bollinger Band in ranging market"
        elif rsi > 70:
            signal = SignalType.SELL
            confidence = min(base_confidence + 0.15, 0.85)
            rationale = "Overbought condition in ranging market - mean reversion opportunity"
        elif rsi > 60 and bb_position is not None and bb_position > 0.7:
            signal = SignalType.SELL
            confidence = base_confidence
            rationale = "Near upper Bollinger Band in ranging market"
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            rationale = "No clear mean reversion signal"
        
        reasoning = {
            "model_version": self.version,
            "strategy": "mean_reversion",
            "regime": regime,
            "rsi": rsi,
            "bb_position": bb_position,
            "rationale": rationale
        }
        
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _avoid_strategy(
        self, 
        symbol: str, 
        regime: str, 
        base_confidence: float
    ) -> AgentOutput:
        """
        Avoid trading in high-vol ranging regime.
        
        Args:
            symbol: Stock symbol
            regime: Regime name
            base_confidence: Base confidence from regime detection
        
        Returns:
            AgentOutput with NO_SIGNAL
        """
        reasoning = {
            "model_version": self.version,
            "strategy": "avoid",
            "regime": regime,
            "rationale": "High volatility + ranging market = unfavorable conditions, avoiding trade"
        }
        
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=SignalType.NO_SIGNAL,
            confidence=base_confidence,
            reasoning=reasoning
        )
    
    def _momentum_breakout_strategy(
        self, 
        symbol: str, 
        regime: str, 
        rsi: Optional[float],
        macd_hist: Optional[float],
        adx: Optional[float],
        base_confidence: float
    ) -> AgentOutput:
        """
        Momentum breakout strategy for low-vol trending regime.
        
        Args:
            symbol: Stock symbol
            regime: Regime name
            rsi: RSI indicator
            macd_hist: MACD histogram
            adx: ADX indicator
            base_confidence: Base confidence from regime detection
        
        Returns:
            AgentOutput
        """
        if macd_hist is None:
            return self._no_signal_output(symbol, "Missing MACD for momentum strategy")
        
        # Look for momentum breakouts
        if macd_hist > 3 and (rsi is None or rsi > 50):
            signal = SignalType.BUY
            confidence = base_confidence + 0.1
            rationale = "Positive momentum breakout in low-vol trend"
        elif macd_hist < -3 and (rsi is None or rsi < 50):
            signal = SignalType.SELL
            confidence = base_confidence + 0.1
            rationale = "Negative momentum breakout in low-vol trend"
        elif macd_hist > 0:
            signal = SignalType.HOLD
            confidence = 0.6
            rationale = "Positive momentum but not strong enough for entry"
        else:
            signal = SignalType.HOLD
            confidence = 0.6
            rationale = "Waiting for clearer momentum signal"
        
        reasoning = {
            "model_version": self.version,
            "strategy": "momentum_breakout",
            "regime": regime,
            "macd_hist": macd_hist,
            "rsi": rsi,
            "adx": adx,
            "rationale": rationale
        }
        
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _no_signal_output(self, symbol: str, reason: str) -> AgentOutput:
        """
        Generate NO_SIGNAL output.
        
        Args:
            symbol: Stock symbol
            reason: Reason for no signal
        
        Returns:
            AgentOutput with NO_SIGNAL
        """
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=SignalType.NO_SIGNAL,
            confidence=0.0,
            reasoning={"reason": reason}
        )
