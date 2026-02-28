"""
Regime Detection Service
Classifies market regimes based on volatility, trend, and hidden Markov models.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from sklearn.mixture import GaussianMixture
from scipy import stats
import talib


class RegimeDetection:
    """Service for detecting market regimes."""
    
    def __init__(self):
        """Initialize the regime detection service."""
        self.hmm_model = None
        self.hmm_trained = False
    
    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect current market regime based on volatility and trend.
        
        Args:
            df: DataFrame with OHLCV data (needs at least 100 bars)
        
        Returns:
            Dictionary with regime classification and confidence
        """
        if df.empty or len(df) < 100:
            raise ValueError("Insufficient data: need at least 100 bars for regime detection")
        
        # Compute returns
        close_prices = df['close'].values
        returns = np.diff(np.log(close_prices))
        
        # Detect volatility regime
        vol_regime, vol_percentile = self._detect_volatility_regime(returns)
        
        # Detect trend regime
        trend_regime, adx_value = self._detect_trend_regime(df)
        
        # Combined regime
        combined_regime = f"{vol_regime}_{trend_regime}"
        
        # Confidence calculation (weighted average of volatility and trend confidence)
        # Volatility confidence: how far from median (0-1 scale)
        vol_confidence = abs(vol_percentile - 0.5) * 2  # Scale from 0.5-1.0 or 0.0-0.5 to 0-1
        
        # Trend confidence: ADX strength (ADX > 25 is strong trend)
        trend_confidence = min(adx_value / 50.0, 1.0) if not np.isnan(adx_value) else 0.5
        
        # Weighted average (60% volatility, 40% trend)
        overall_confidence = (vol_confidence * 0.6) + (trend_confidence * 0.4)
        
        result = {
            "volatility": vol_regime,
            "volatility_percentile": float(vol_percentile),
            "trend": trend_regime,
            "trend_strength": float(adx_value) if not np.isnan(adx_value) else 25.0,
            "combined": combined_regime,
            "confidence": float(overall_confidence)
        }
        
        # Add HMM regime if model is trained
        if self.hmm_trained:
            try:
                hmm_state = self._hmm_predict(df)
                result['hmm_state'] = int(hmm_state)
                result['hmm_regime'] = self._interpret_hmm_state(hmm_state)
            except Exception as e:
                result['hmm_state'] = None
                result['hmm_regime'] = None
        
        return result
    
    def _detect_volatility_regime(self, returns: np.ndarray, window: int = 20) -> Tuple[str, float]:
        """
        Detect volatility regime based on rolling standard deviation.
        
        Args:
            returns: Array of log returns
            window: Rolling window for volatility calculation
        
        Returns:
            Tuple of (regime_name, percentile_value)
        """
        # Calculate rolling volatility (annualized)
        rolling_vol = pd.Series(returns).rolling(window=window).std() * np.sqrt(252)
        
        # Get current volatility
        current_vol = rolling_vol.iloc[-1]
        
        # Calculate percentile of current volatility in historical distribution
        percentile = stats.percentileofscore(rolling_vol.dropna(), current_vol) / 100.0
        
        # Classify regime
        if percentile > 0.75:
            regime = "high_vol"
        elif percentile > 0.40:
            regime = "medium_vol"
        else:
            regime = "low_vol"
        
        return regime, percentile
    
    def _detect_trend_regime(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Detect trend regime using ADX and price channels.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Tuple of (regime_name, adx_value)
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Calculate ADX
        adx = talib.ADX(high, low, close, timeperiod=14)
        current_adx = adx[-1] if not np.isnan(adx[-1]) else 25.0
        
        # Calculate directional indicators
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=14)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
        
        current_plus_di = plus_di[-1] if not np.isnan(plus_di[-1]) else 25.0
        current_minus_di = minus_di[-1] if not np.isnan(minus_di[-1]) else 25.0
        
        # Classify trend regime
        if current_adx > 25:
            # Strong trend
            if current_plus_di > current_minus_di:
                regime = "trending_up"
            else:
                regime = "trending_down"
        elif current_adx > 20:
            # Moderate trend
            regime = "trending"
        else:
            # Weak trend / ranging
            regime = "ranging"
        
        return regime, float(current_adx)
    
    def train_hmm(self, df: pd.DataFrame, n_states: int = 3) -> Dict[str, Any]:
        """
        Train a Hidden Markov Model (using Gaussian Mixture as approximation).
        
        Args:
            df: DataFrame with OHLCV data (needs substantial history, 500+ bars)
            n_states: Number of hidden states (default 3: bull, bear, sideways)
        
        Returns:
            Dictionary with training results
        """
        if len(df) < 500:
            raise ValueError("Insufficient data: need at least 500 bars for HMM training")
        
        # Feature engineering for HMM
        features = self._extract_hmm_features(df)
        
        # Train Gaussian Mixture Model (approximation of HMM)
        self.hmm_model = GaussianMixture(
            n_components=n_states,
            covariance_type='full',
            max_iter=100,
            random_state=42
        )
        
        self.hmm_model.fit(features)
        self.hmm_trained = True
        
        # Predict states for the data
        states = self.hmm_model.predict(features)
        
        # Calculate state statistics
        state_stats = {}
        for state in range(n_states):
            state_mask = states == state
            state_returns = features[state_mask, 0]  # First feature is returns
            
            state_stats[f'state_{state}'] = {
                'count': int(np.sum(state_mask)),
                'mean_return': float(np.mean(state_returns)),
                'volatility': float(np.std(state_returns)),
                'sharpe': float(np.mean(state_returns) / np.std(state_returns)) if np.std(state_returns) > 0 else 0.0
            }
        
        return {
            'n_states': n_states,
            'trained': True,
            'data_points': len(features),
            'state_stats': state_stats,
            'aic': float(self.hmm_model.aic(features)),
            'bic': float(self.hmm_model.bic(features))
        }
    
    def _extract_hmm_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract features for HMM training.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            2D array of features (n_samples, n_features)
        """
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
        
        # Returns
        returns = np.diff(np.log(close), prepend=np.log(close[0]))
        
        # Rolling volatility (20-day)
        rolling_vol = pd.Series(returns).rolling(window=20).std().fillna(method='bfill').values
        
        # Volume ratio (current / 20-day average)
        volume_sma = pd.Series(volume).rolling(window=20).mean().fillna(method='bfill').values
        volume_ratio = volume / (volume_sma + 1e-10)
        
        # RSI
        rsi = talib.RSI(close, timeperiod=14)
        rsi = pd.Series(rsi).fillna(50.0).values  # Fill NaN with neutral value
        
        # Normalize RSI to [-1, 1]
        rsi_normalized = (rsi - 50) / 50
        
        # Stack features
        features = np.column_stack([
            returns,
            rolling_vol,
            volume_ratio,
            rsi_normalized
        ])
        
        return features
    
    def _hmm_predict(self, df: pd.DataFrame) -> int:
        """
        Predict current HMM state.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Current state (0, 1, or 2)
        """
        if not self.hmm_trained or self.hmm_model is None:
            raise ValueError("HMM model not trained. Call train_hmm() first.")
        
        # Extract features for the most recent window
        features = self._extract_hmm_features(df.tail(100))
        
        # Predict state for most recent observation
        state = self.hmm_model.predict(features[-1:])
        
        return int(state[0])
    
    def _interpret_hmm_state(self, state: int) -> str:
        """
        Interpret HMM state into human-readable regime.
        
        Args:
            state: HMM state (0, 1, or 2)
        
        Returns:
            Regime name
        """
        # This mapping depends on the state statistics from training
        # Typically: highest mean return = bull, lowest = bear, middle = sideways
        # For simplicity, we use a fixed mapping
        state_map = {
            0: "bear_market",
            1: "sideways_market",
            2: "bull_market"
        }
        
        return state_map.get(state, f"state_{state}")
    
    def get_regime_stats(self, df: pd.DataFrame, regime_col: str = 'combined') -> Dict[str, Any]:
        """
        Calculate statistics for different regime periods.
        
        Args:
            df: DataFrame with OHLCV data and regime classifications
            regime_col: Column name containing regime classifications
        
        Returns:
            Dictionary with regime statistics
        """
        if regime_col not in df.columns:
            raise ValueError(f"Column {regime_col} not found in DataFrame")
        
        close = df['close'].values
        returns = np.diff(np.log(close), prepend=np.log(close[0]))
        df['returns'] = returns
        
        regime_stats = {}
        unique_regimes = df[regime_col].unique()
        
        for regime in unique_regimes:
            regime_data = df[df[regime_col] == regime]
            regime_returns = regime_data['returns'].values
            
            regime_stats[regime] = {
                'count': len(regime_data),
                'mean_return': float(np.mean(regime_returns)),
                'volatility': float(np.std(regime_returns)),
                'sharpe': float(np.mean(regime_returns) / np.std(regime_returns)) if np.std(regime_returns) > 0 else 0.0,
                'max_drawdown': float(self._calculate_max_drawdown(regime_data['close'].values))
            }
        
        return regime_stats
    
    def _calculate_max_drawdown(self, prices: np.ndarray) -> float:
        """Calculate maximum drawdown from price series."""
        cumulative = np.maximum.accumulate(prices)
        drawdown = (prices - cumulative) / cumulative
        return float(np.min(drawdown))


# Singleton instance
regime_detection = RegimeDetection()
