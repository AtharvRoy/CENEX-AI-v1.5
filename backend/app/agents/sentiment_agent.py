"""
Sentiment Agent
News sentiment-based analysis using FinBERT scores.
"""

import os
import logging
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

from app.agents.base_agent import BaseAgent, AgentOutput, SignalType

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """
    Sentiment-based analysis agent using news data.
    
    Features:
    - FinBERT sentiment scores
    - News volume and freshness
    - Sentiment trend detection
    - Logistic regression for signal mapping (optional ML model)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Sentiment Agent.
        
        Args:
            model_path: Path to trained model (optional)
        """
        super().__init__(name="sentiment", version="1.0")
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Load trained sentiment model (optional).
        
        Args:
            model_path: Path to model file
        """
        if model_path is None:
            model_path = os.path.join(
                Path(__file__).parent.parent.parent,
                "models",
                "sentiment_agent_v1.pkl"
            )
        
        if not os.path.exists(model_path):
            logger.info(f"No sentiment model found at {model_path}. Using rule-based approach.")
            self._model = None
            return
        
        try:
            import joblib
            self._model = joblib.load(model_path)
            logger.info(f"Sentiment agent model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Error loading sentiment model: {e}")
            self._model = None
    
    async def analyze(
        self, 
        symbol: str, 
        features: Dict[str, Any],
        **kwargs
    ) -> AgentOutput:
        """
        Analyze symbol using sentiment data.
        
        Args:
            symbol: Stock symbol
            features: Feature vector dictionary
            **kwargs: Additional parameters
        
        Returns:
            AgentOutput with signal and confidence
        """
        # Validate features
        if not self._validate_features(features, ['sentiment']):
            return self._no_signal_output(symbol, "Missing sentiment data")
        
        sentiment_data = features.get('sentiment', {})
        
        # Use ML model if available, otherwise use rules
        if self._model is not None:
            return await self._ml_analysis(symbol, sentiment_data)
        else:
            return await self._rule_based_analysis(symbol, sentiment_data)
    
    async def _ml_analysis(self, symbol: str, sentiment_data: Dict[str, Any]) -> AgentOutput:
        """
        ML-based sentiment analysis.
        
        Args:
            symbol: Stock symbol
            sentiment_data: Sentiment analysis data
        
        Returns:
            AgentOutput
        """
        try:
            # Extract features for ML model
            sentiment_score = sentiment_data.get('sentiment_score', 0.0)
            news_count = sentiment_data.get('news_count', 0)
            freshness = sentiment_data.get('freshness_hours', 48)
            
            # Feature vector: [sentiment_score, news_count_normalized, freshness_normalized]
            feature_vector = [
                sentiment_score,
                min(news_count / 10.0, 1.0),  # Normalize to 0-1
                max(0, 1.0 - freshness / 48.0)  # Fresher = higher score
            ]
            
            # Predict
            probs = self._model.predict_proba([feature_vector])[0]
            predicted_class = np.argmax(probs)
            
            # Map to signal (0=SELL, 1=HOLD, 2=BUY)
            signal_map = {0: SignalType.SELL, 1: SignalType.HOLD, 2: SignalType.BUY}
            signal = signal_map.get(predicted_class, SignalType.HOLD)
            confidence = float(probs[predicted_class])
            
            reasoning = {
                "model_version": self.version,
                "prediction_method": "logistic_regression",
                "sentiment_score": sentiment_score,
                "news_count": news_count,
                "freshness_hours": freshness,
                "probability_distribution": {
                    "SELL": float(probs[0]),
                    "HOLD": float(probs[1]),
                    "BUY": float(probs[2]),
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
            logger.error(f"Error in sentiment ML analysis for {symbol}: {e}")
            return self._no_signal_output(symbol, f"ML error: {str(e)}")
    
    async def _rule_based_analysis(self, symbol: str, sentiment_data: Dict[str, Any]) -> AgentOutput:
        """
        Rule-based sentiment analysis.
        
        Logic:
        - Sentiment > 0.3 + rising → BUY
        - Sentiment < -0.3 + falling → SELL
        - Confidence based on news volume and freshness
        
        Args:
            symbol: Stock symbol
            sentiment_data: Sentiment analysis data
        
        Returns:
            AgentOutput
        """
        try:
            sentiment_score = sentiment_data.get('sentiment_score', 0.0)
            sentiment_label = sentiment_data.get('sentiment_label', 'neutral')
            news_count = sentiment_data.get('news_count', 0)
            freshness_hours = sentiment_data.get('freshness_hours', 48)
            
            # No news = no signal
            if news_count == 0:
                return self._no_signal_output(symbol, "No news available")
            
            # Determine signal based on sentiment score
            if sentiment_score > 0.4:
                signal = SignalType.STRONG_BUY
                base_confidence = 0.75
            elif sentiment_score > 0.2:
                signal = SignalType.BUY
                base_confidence = 0.65
            elif sentiment_score < -0.4:
                signal = SignalType.STRONG_SELL
                base_confidence = 0.75
            elif sentiment_score < -0.2:
                signal = SignalType.SELL
                base_confidence = 0.65
            else:
                signal = SignalType.HOLD
                base_confidence = 0.5
            
            # Adjust confidence based on news volume and freshness
            volume_factor = min(news_count / 5.0, 1.0)  # More news = higher confidence
            freshness_factor = max(0, 1.0 - freshness_hours / 48.0)  # Fresher = higher confidence
            
            confidence = base_confidence * (0.6 + 0.2 * volume_factor + 0.2 * freshness_factor)
            confidence = min(confidence, 0.95)  # Cap at 95%
            
            # Build reasoning
            reasoning = {
                "model_version": self.version,
                "prediction_method": "rule_based",
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "news_count": news_count,
                "freshness_hours": freshness_hours,
                "volume_factor": volume_factor,
                "freshness_factor": freshness_factor,
                "signal_rationale": self._get_signal_rationale(
                    sentiment_score, 
                    sentiment_label, 
                    news_count
                )
            }
            
            return AgentOutput(
                agent_name=self.name,
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )
        
        except Exception as e:
            logger.error(f"Error in sentiment rule-based analysis for {symbol}: {e}")
            return self._no_signal_output(symbol, f"Analysis error: {str(e)}")
    
    def _get_signal_rationale(
        self, 
        sentiment_score: float, 
        sentiment_label: str, 
        news_count: int
    ) -> str:
        """
        Generate human-readable signal rationale.
        
        Args:
            sentiment_score: Sentiment score
            sentiment_label: Sentiment label
            news_count: Number of news articles
        
        Returns:
            Rationale string
        """
        if sentiment_score > 0.3:
            return f"Positive sentiment ({sentiment_label}) with {news_count} news articles suggests bullish outlook"
        elif sentiment_score < -0.3:
            return f"Negative sentiment ({sentiment_label}) with {news_count} news articles suggests bearish outlook"
        else:
            return f"Neutral sentiment ({sentiment_label}) with {news_count} news articles suggests wait-and-see approach"
    
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
