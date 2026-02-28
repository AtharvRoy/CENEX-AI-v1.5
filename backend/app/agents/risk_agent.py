"""
Risk Agent
Position sizing, stop-loss, and risk management validation.
"""

import logging
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent, AgentOutput, SignalType

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    """
    Risk management and position sizing agent.
    
    Features:
    - Position sizing (Kelly Criterion / fixed %)
    - Stop-loss calculation (ATR-based)
    - Risk-reward ratio validation
    - Liquidity checks
    - Volatility assessment
    """
    
    def __init__(
        self, 
        max_position_size_pct: float = 10.0,
        max_risk_per_trade_pct: float = 2.0,
        min_risk_reward_ratio: float = 1.5
    ):
        """
        Initialize Risk Agent.
        
        Args:
            max_position_size_pct: Maximum position size as % of portfolio
            max_risk_per_trade_pct: Maximum risk per trade as % of portfolio
            min_risk_reward_ratio: Minimum acceptable risk-reward ratio
        """
        super().__init__(name="risk", version="1.0")
        
        self.max_position_size_pct = max_position_size_pct
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio
    
    def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Risk agent uses rule-based calculations, no model to load.
        
        Args:
            model_path: Not used
        """
        logger.info("Risk agent uses rule-based calculations, no model loading required")
    
    async def analyze(
        self, 
        symbol: str, 
        features: Dict[str, Any],
        entry_price: Optional[float] = None,
        target_price: Optional[float] = None,
        portfolio_value: float = 100000.0,
        **kwargs
    ) -> AgentOutput:
        """
        Analyze risk for a potential trade.
        
        Args:
            symbol: Stock symbol
            features: Feature vector dictionary
            entry_price: Proposed entry price (defaults to current price)
            target_price: Target price for trade (optional)
            portfolio_value: Total portfolio value
            **kwargs: Additional parameters
        
        Returns:
            AgentOutput with APPROVE/REJECT signal and risk metrics
        """
        # Validate features
        if not self._validate_features(features, ['price', 'technical']):
            return self._reject_output(symbol, "Missing price or technical data")
        
        price_data = features.get('price', {})
        technical = features.get('technical', {})
        regime_data = features.get('regime', {})
        
        return await self._risk_assessment(
            symbol, 
            price_data, 
            technical, 
            regime_data,
            entry_price, 
            target_price, 
            portfolio_value
        )
    
    async def _risk_assessment(
        self,
        symbol: str,
        price_data: Dict[str, Any],
        technical: Dict[str, Any],
        regime_data: Dict[str, Any],
        entry_price: Optional[float],
        target_price: Optional[float],
        portfolio_value: float
    ) -> AgentOutput:
        """
        Perform comprehensive risk assessment.
        
        Args:
            symbol: Stock symbol
            price_data: Price data
            technical: Technical indicators
            regime_data: Regime data
            entry_price: Entry price
            target_price: Target price
            portfolio_value: Portfolio value
        
        Returns:
            AgentOutput with risk assessment
        """
        try:
            # Get current price
            current_price = price_data.get('close')
            if current_price is None:
                return self._reject_output(symbol, "Missing current price")
            
            if entry_price is None:
                entry_price = current_price
            
            # Get ATR for stop-loss calculation
            atr = technical.get('atr_14')
            if atr is None:
                return self._reject_output(symbol, "Missing ATR for stop-loss calculation")
            
            # Get volatility
            volatility = technical.get('volatility_20d', 0.02)
            
            # Get average volume for liquidity check
            volume = price_data.get('volume', 0)
            
            # Calculate stop-loss (2 * ATR below entry)
            stop_loss = entry_price - (2.0 * atr)
            risk_per_share = entry_price - stop_loss
            
            # If no target provided, use 3 * ATR above entry (1.5:1 risk-reward)
            if target_price is None:
                target_price = entry_price + (3.0 * atr)
            
            reward_per_share = target_price - entry_price
            
            # Calculate risk-reward ratio
            if risk_per_share > 0:
                risk_reward_ratio = reward_per_share / risk_per_share
            else:
                return self._reject_output(symbol, "Invalid risk calculation (stop above entry)")
            
            # Check minimum risk-reward ratio
            if risk_reward_ratio < self.min_risk_reward_ratio:
                return self._reject_output(
                    symbol, 
                    f"Risk-reward ratio {risk_reward_ratio:.2f} below minimum {self.min_risk_reward_ratio}"
                )
            
            # Calculate position size based on risk
            # Risk = (Entry - Stop) * Position Size
            # Max Risk = Portfolio Value * Max Risk %
            max_risk_amount = portfolio_value * (self.max_risk_per_trade_pct / 100.0)
            position_size_by_risk = max_risk_amount / risk_per_share
            
            # Calculate position size based on max position %
            max_position_value = portfolio_value * (self.max_position_size_pct / 100.0)
            position_size_by_value = max_position_value / entry_price
            
            # Use the more conservative (smaller) position size
            position_size = min(position_size_by_risk, position_size_by_value)
            position_value = position_size * entry_price
            position_size_pct = (position_value / portfolio_value) * 100.0
            
            # Liquidity check - ensure sufficient volume
            # Rule of thumb: position should be < 1% of average daily volume
            if volume > 0 and position_size > (volume * 0.01):
                liquidity_check = "WARNING"
                liquidity_note = "Position size may be too large relative to volume"
            else:
                liquidity_check = "PASS"
                liquidity_note = "Sufficient liquidity"
            
            # Volatility assessment
            volatility_percentile = self._calculate_volatility_percentile(volatility)
            
            if volatility_percentile > 0.8:
                volatility_warning = "High volatility - consider reducing position size"
                # Reduce position size by 30% in high volatility
                position_size *= 0.7
                position_value = position_size * entry_price
                position_size_pct = (position_value / portfolio_value) * 100.0
            else:
                volatility_warning = None
            
            # Calculate overall risk score (0 = no risk, 1 = maximum risk)
            # Lower is better
            risk_factors = []
            
            # Factor 1: Position size relative to max
            size_risk = position_size_pct / self.max_position_size_pct
            risk_factors.append(size_risk)
            
            # Factor 2: Volatility
            risk_factors.append(volatility_percentile)
            
            # Factor 3: Risk-reward (inverse - higher RR = lower risk)
            rr_risk = max(0, 1.0 - (risk_reward_ratio / 5.0))  # Normalize to 0-1
            risk_factors.append(rr_risk)
            
            # Overall risk score (average of factors)
            risk_score = sum(risk_factors) / len(risk_factors)
            
            # Determine approval
            if risk_score > 0.8:
                signal = SignalType.REJECT
                confidence = 0.9
                approval_note = "Risk too high - trade rejected"
            elif liquidity_check == "WARNING":
                signal = SignalType.REJECT
                confidence = 0.8
                approval_note = "Insufficient liquidity - trade rejected"
            else:
                signal = SignalType.APPROVE
                confidence = 1.0 - risk_score  # Lower risk = higher confidence
                approval_note = "Risk acceptable - trade approved"
            
            # Build reasoning
            reasoning = {
                "model_version": self.version,
                "risk_score": round(risk_score, 3),
                "position_size": int(position_size),
                "position_value": round(position_value, 2),
                "position_size_pct": round(position_size_pct, 2),
                "entry_price": round(entry_price, 2),
                "stop_loss": round(stop_loss, 2),
                "target_price": round(target_price, 2),
                "risk_per_share": round(risk_per_share, 2),
                "reward_per_share": round(reward_per_share, 2),
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "atr": round(atr, 2),
                "volatility_percentile": round(volatility_percentile, 2),
                "liquidity_check": liquidity_check,
                "liquidity_note": liquidity_note,
                "volatility_warning": volatility_warning,
                "approval_note": approval_note,
                "portfolio_value": portfolio_value,
                "max_risk_per_trade_pct": self.max_risk_per_trade_pct,
                "max_position_size_pct": self.max_position_size_pct,
            }
            
            return AgentOutput(
                agent_name=self.name,
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )
        
        except Exception as e:
            logger.error(f"Error in risk assessment for {symbol}: {e}")
            return self._reject_output(symbol, f"Risk assessment error: {str(e)}")
    
    def _calculate_volatility_percentile(self, volatility: float) -> float:
        """
        Calculate volatility percentile (0-1).
        
        Rough benchmarks:
        - 0.01 (1%) = very low volatility → 0.2
        - 0.02 (2%) = normal → 0.5
        - 0.03 (3%) = high → 0.75
        - 0.05+ (5%+) = very high → 0.95
        
        Args:
            volatility: Volatility value
        
        Returns:
            Percentile (0-1)
        """
        if volatility < 0.015:
            return 0.2
        elif volatility < 0.025:
            return 0.5
        elif volatility < 0.035:
            return 0.75
        else:
            return min(0.95, 0.75 + (volatility - 0.035) * 5)
    
    def _reject_output(self, symbol: str, reason: str) -> AgentOutput:
        """
        Generate REJECT output.
        
        Args:
            symbol: Stock symbol
            reason: Reason for rejection
        
        Returns:
            AgentOutput with REJECT signal
        """
        return AgentOutput(
            agent_name=self.name,
            symbol=symbol,
            signal=SignalType.REJECT,
            confidence=1.0,
            reasoning={
                "reason": reason,
                "approval_note": f"Trade rejected: {reason}"
            }
        )
