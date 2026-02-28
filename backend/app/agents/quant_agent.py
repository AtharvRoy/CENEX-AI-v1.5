"""
Quant Agent
LightGBM-based quantitative analysis agent using technical indicators.
"""

import os
import logging
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

from app.agents.base_agent import BaseAgent, AgentOutput, SignalType

logger = logging.getLogger(__name__)


class QuantAgent(BaseAgent):
    """
    Quantitative analysis agent using machine learning.
    
    Features:
    - LightGBM classifier (5-class: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
    - Technical indicators as features
    - Feature importance analysis
    """
    
    # Feature columns expected by the model
    FEATURE_COLS = [
        'rsi_14', 'rsi_28',
        'macd', 'macd_signal', 'macd_hist',
        'adx_14',
        'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
        'atr_14',
        'obv_pct',
        'vwap_distance',
        'volume_sma_ratio',
        'returns_5d', 'returns_20d',
        'volatility_20d',
        'momentum_10d',
    ]
    
    # Label mapping
    LABEL_MAP = {
        0: SignalType.STRONG_SELL,
        1: SignalType.SELL,
        2: SignalType.HOLD,
        3: SignalType.BUY,
        4: SignalType.STRONG_BUY,
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Quant Agent.
        
        Args:
            model_path: Path to trained LightGBM model
        """
        super().__init__(name="quant", version="1.0")
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Load trained LightGBM model.
        
        Args:
            model_path: Path to model file (.pkl)
        """
        if model_path is None:
            # Default model path
            model_path = os.path.join(
                Path(__file__).parent.parent.parent,
                "models",
                "quant_agent_v1.pkl"
            )
        
        if not os.path.exists(model_path):
            logger.warning(f"Model not found at {model_path}. Agent will use rule-based fallback.")
            self._model = None
            return
        
        try:
            import joblib
            self._model = joblib.load(model_path)
            logger.info(f"Quant agent model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._model = None
    
    async def analyze(
        self, 
        symbol: str, 
        features: Dict[str, Any],
        **kwargs
    ) -> AgentOutput:
        """
        Analyze symbol using quantitative model.
        
        Args:
            symbol: Stock symbol
            features: Feature vector dictionary
            **kwargs: Additional parameters
        
        Returns:
            AgentOutput with signal and confidence
        """
        # Validate features
        if not self._validate_features(features, ['technical']):
            return self._no_signal_output(symbol, "Missing technical features")
        
        technical = features.get('technical', {})
        
        # Use ML model if available, otherwise fallback to rules
        if self._model is not None:
            return await self._ml_analysis(symbol, technical)
        else:
            return await self._rule_based_analysis(symbol, technical)
    
    async def _ml_analysis(self, symbol: str, technical: Dict[str, Any]) -> AgentOutput:
        """
        ML-based analysis using LightGBM.
        
        Args:
            symbol: Stock symbol
            technical: Technical indicators
        
        Returns:
            AgentOutput
        """
        try:
            # Extract features
            feature_vector = self._extract_features(technical)
            
            if feature_vector is None:
                return self._no_signal_output(symbol, "Incomplete feature vector")
            
            # Predict
            probs = self._model.predict_proba([feature_vector])[0]
            predicted_class = np.argmax(probs)
            confidence = float(probs[predicted_class])
            
            signal = self.LABEL_MAP[predicted_class]
            
            # Get feature importance
            feature_importance = {}
            if hasattr(self._model, 'feature_importance'):
                importances = self._model.feature_importance(importance_type='gain')
                # Top 5 features
                top_indices = np.argsort(importances)[-5:][::-1]
                for idx in top_indices:
                    if idx < len(self.FEATURE_COLS):
                        feature_importance[self.FEATURE_COLS[idx]] = float(importances[idx])
            
            # Build reasoning
            reasoning = {
                "model_version": self.version,
                "prediction_method": "lightgbm",
                "probability_distribution": {
                    "STRONG_SELL": float(probs[0]),
                    "SELL": float(probs[1]),
                    "HOLD": float(probs[2]),
                    "BUY": float(probs[3]),
                    "STRONG_BUY": float(probs[4]),
                },
                "feature_importance": feature_importance,
                "top_features": list(feature_importance.keys())[:3],
            }
            
            return AgentOutput(
                agent_name=self.name,
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )
        
        except Exception as e:
            logger.error(f"Error in ML analysis for {symbol}: {e}")
            return self._no_signal_output(symbol, f"ML error: {str(e)}")
    
    async def _rule_based_analysis(self, symbol: str, technical: Dict[str, Any]) -> AgentOutput:
        """
        Rule-based fallback analysis.
        
        Args:
            symbol: Stock symbol
            technical: Technical indicators
        
        Returns:
            AgentOutput
        """
        try:
            # Extract key indicators
            rsi = technical.get('rsi_14')
            macd_hist = technical.get('macd_hist')
            adx = technical.get('adx_14')
            bb_position = technical.get('bb_position')  # Where price is in BB band
            
            # Check if we have minimum indicators
            if rsi is None or macd_hist is None:
                return self._no_signal_output(symbol, "Insufficient indicators for rule-based analysis")
            
            # Simple rule-based logic
            buy_signals = 0
            sell_signals = 0
            confidence_factors = []
            
            # RSI signals
            if rsi < 30:
                buy_signals += 2
                confidence_factors.append("oversold_rsi")
            elif rsi < 40:
                buy_signals += 1
            elif rsi > 70:
                sell_signals += 2
                confidence_factors.append("overbought_rsi")
            elif rsi > 60:
                sell_signals += 1
            
            # MACD signals
            if macd_hist > 0:
                buy_signals += 1
                if macd_hist > 5:
                    confidence_factors.append("strong_macd")
            else:
                sell_signals += 1
                if macd_hist < -5:
                    confidence_factors.append("weak_macd")
            
            # ADX (trend strength)
            if adx and adx > 25:
                confidence_factors.append("strong_trend")
            
            # Bollinger Band position
            if bb_position is not None:
                if bb_position < 0.2:
                    buy_signals += 1
                    confidence_factors.append("bb_oversold")
                elif bb_position > 0.8:
                    sell_signals += 1
                    confidence_factors.append("bb_overbought")
            
            # Determine signal
            net_signal = buy_signals - sell_signals
            
            if net_signal >= 3:
                signal = SignalType.STRONG_BUY
                confidence = min(0.75, 0.5 + net_signal * 0.1)
            elif net_signal >= 1:
                signal = SignalType.BUY
                confidence = min(0.65, 0.5 + net_signal * 0.1)
            elif net_signal <= -3:
                signal = SignalType.STRONG_SELL
                confidence = min(0.75, 0.5 + abs(net_signal) * 0.1)
            elif net_signal <= -1:
                signal = SignalType.SELL
                confidence = min(0.65, 0.5 + abs(net_signal) * 0.1)
            else:
                signal = SignalType.HOLD
                confidence = 0.5
            
            reasoning = {
                "model_version": self.version,
                "prediction_method": "rule_based",
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "net_signal": net_signal,
                "confidence_factors": confidence_factors,
                "indicators_used": {
                    "rsi_14": rsi,
                    "macd_hist": macd_hist,
                    "adx_14": adx,
                    "bb_position": bb_position,
                }
            }
            
            return AgentOutput(
                agent_name=self.name,
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )
        
        except Exception as e:
            logger.error(f"Error in rule-based analysis for {symbol}: {e}")
            return self._no_signal_output(symbol, f"Rule-based error: {str(e)}")
    
    def _extract_features(self, technical: Dict[str, Any]) -> Optional[list]:
        """
        Extract feature vector for ML model.
        
        Args:
            technical: Technical indicators
        
        Returns:
            Feature vector as list, or None if incomplete
        """
        feature_vector = []
        
        for col in self.FEATURE_COLS:
            value = technical.get(col)
            if value is None:
                # Try to handle missing values
                logger.warning(f"Missing feature: {col}")
                feature_vector.append(0.0)  # Default to 0
            else:
                feature_vector.append(float(value))
        
        return feature_vector
    
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
