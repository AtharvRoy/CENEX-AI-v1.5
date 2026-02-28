"""
Technical Indicators Service
Computes momentum, trend, volatility, and volume indicators using TA-Lib and pandas-ta.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import talib
import pandas_ta as ta


class TechnicalIndicators:
    """Service for computing technical indicators on OHLCV data."""
    
    def __init__(self):
        """Initialize the technical indicators service."""
        pass
    
    def compute_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute all technical indicators on OHLCV data.
        
        Args:
            df: DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
        
        Returns:
            Dictionary with all computed indicators
        """
        if df.empty or len(df) < 50:
            raise ValueError("Insufficient data: need at least 50 bars for indicator calculation")
        
        # Ensure DataFrame has required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Convert to numpy arrays for TA-Lib
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        volume = df['volume'].values
        
        indicators = {}
        
        # Momentum Indicators
        indicators.update(self._compute_momentum(close_prices, high_prices, low_prices))
        
        # Trend Indicators
        indicators.update(self._compute_trend(close_prices, high_prices, low_prices))
        
        # Volatility Indicators
        indicators.update(self._compute_volatility(close_prices, high_prices, low_prices))
        
        # Volume Indicators
        indicators.update(self._compute_volume(close_prices, high_prices, low_prices, volume, df))
        
        # Price action
        indicators['price_close'] = float(close_prices[-1])
        indicators['price_change'] = float(close_prices[-1] - close_prices[-2])
        indicators['price_change_pct'] = float((close_prices[-1] - close_prices[-2]) / close_prices[-2] * 100)
        
        return indicators
    
    def _compute_momentum(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Compute momentum indicators."""
        indicators = {}
        
        # RSI (Relative Strength Index)
        rsi_14 = talib.RSI(close, timeperiod=14)
        indicators['rsi_14'] = float(rsi_14[-1]) if not np.isnan(rsi_14[-1]) else 50.0
        
        # Stochastic Oscillator
        slowk, slowd = talib.STOCH(high, low, close, 
                                    fastk_period=14, 
                                    slowk_period=3, 
                                    slowd_period=3)
        indicators['stoch_k'] = float(slowk[-1]) if not np.isnan(slowk[-1]) else 50.0
        indicators['stoch_d'] = float(slowd[-1]) if not np.isnan(slowd[-1]) else 50.0
        
        # Rate of Change (ROC)
        roc = talib.ROC(close, timeperiod=10)
        indicators['roc_10'] = float(roc[-1]) if not np.isnan(roc[-1]) else 0.0
        
        # Williams %R
        willr = talib.WILLR(high, low, close, timeperiod=14)
        indicators['willr_14'] = float(willr[-1]) if not np.isnan(willr[-1]) else -50.0
        
        # Commodity Channel Index (CCI)
        cci = talib.CCI(high, low, close, timeperiod=14)
        indicators['cci_14'] = float(cci[-1]) if not np.isnan(cci[-1]) else 0.0
        
        # Money Flow Index (MFI) - requires volume, handled in volume section
        
        return indicators
    
    def _compute_trend(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Compute trend indicators."""
        indicators = {}
        
        # MACD (Moving Average Convergence Divergence)
        macd, macd_signal, macd_hist = talib.MACD(close, 
                                                   fastperiod=12, 
                                                   slowperiod=26, 
                                                   signalperiod=9)
        indicators['macd'] = float(macd[-1]) if not np.isnan(macd[-1]) else 0.0
        indicators['macd_signal'] = float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else 0.0
        indicators['macd_hist'] = float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else 0.0
        
        # ADX (Average Directional Index)
        adx = talib.ADX(high, low, close, timeperiod=14)
        indicators['adx_14'] = float(adx[-1]) if not np.isnan(adx[-1]) else 25.0
        
        # Directional Movement Indicators
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=14)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
        indicators['plus_di'] = float(plus_di[-1]) if not np.isnan(plus_di[-1]) else 25.0
        indicators['minus_di'] = float(minus_di[-1]) if not np.isnan(minus_di[-1]) else 25.0
        
        # Aroon Indicator
        aroon_down, aroon_up = talib.AROON(high, low, timeperiod=25)
        indicators['aroon_up'] = float(aroon_up[-1]) if not np.isnan(aroon_up[-1]) else 50.0
        indicators['aroon_down'] = float(aroon_down[-1]) if not np.isnan(aroon_down[-1]) else 50.0
        
        # Parabolic SAR
        sar = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
        indicators['sar'] = float(sar[-1]) if not np.isnan(sar[-1]) else float(close[-1])
        indicators['sar_signal'] = 1.0 if close[-1] > sar[-1] else -1.0
        
        # Moving Averages
        sma_20 = talib.SMA(close, timeperiod=20)
        sma_50 = talib.SMA(close, timeperiod=50)
        ema_12 = talib.EMA(close, timeperiod=12)
        ema_26 = talib.EMA(close, timeperiod=26)
        
        indicators['sma_20'] = float(sma_20[-1]) if not np.isnan(sma_20[-1]) else float(close[-1])
        indicators['sma_50'] = float(sma_50[-1]) if not np.isnan(sma_50[-1]) else float(close[-1])
        indicators['ema_12'] = float(ema_12[-1]) if not np.isnan(ema_12[-1]) else float(close[-1])
        indicators['ema_26'] = float(ema_26[-1]) if not np.isnan(ema_26[-1]) else float(close[-1])
        
        # Price vs MA signals
        indicators['price_vs_sma20'] = float((close[-1] - sma_20[-1]) / sma_20[-1] * 100) if not np.isnan(sma_20[-1]) else 0.0
        indicators['price_vs_sma50'] = float((close[-1] - sma_50[-1]) / sma_50[-1] * 100) if not np.isnan(sma_50[-1]) else 0.0
        
        return indicators
    
    def _compute_volatility(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Compute volatility indicators."""
        indicators = {}
        
        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, 
                                            timeperiod=20, 
                                            nbdevup=2, 
                                            nbdevdn=2, 
                                            matype=0)
        indicators['bb_upper'] = float(upper[-1]) if not np.isnan(upper[-1]) else float(close[-1] * 1.02)
        indicators['bb_middle'] = float(middle[-1]) if not np.isnan(middle[-1]) else float(close[-1])
        indicators['bb_lower'] = float(lower[-1]) if not np.isnan(lower[-1]) else float(close[-1] * 0.98)
        indicators['bb_width'] = float((upper[-1] - lower[-1]) / middle[-1] * 100) if not np.isnan(upper[-1]) else 4.0
        indicators['bb_position'] = float((close[-1] - lower[-1]) / (upper[-1] - lower[-1]) * 100) if not np.isnan(upper[-1]) else 50.0
        
        # ATR (Average True Range)
        atr_14 = talib.ATR(high, low, close, timeperiod=14)
        indicators['atr_14'] = float(atr_14[-1]) if not np.isnan(atr_14[-1]) else float(close[-1] * 0.02)
        indicators['atr_pct'] = float(atr_14[-1] / close[-1] * 100) if not np.isnan(atr_14[-1]) else 2.0
        
        # Keltner Channels (using EMA and ATR)
        ema_20 = talib.EMA(close, timeperiod=20)
        keltner_upper = ema_20 + (2 * atr_14)
        keltner_lower = ema_20 - (2 * atr_14)
        indicators['keltner_upper'] = float(keltner_upper[-1]) if not np.isnan(keltner_upper[-1]) else float(close[-1] * 1.04)
        indicators['keltner_lower'] = float(keltner_lower[-1]) if not np.isnan(keltner_lower[-1]) else float(close[-1] * 0.96)
        
        # Historical Volatility (20-day rolling standard deviation)
        returns = np.diff(np.log(close))
        hist_vol = np.std(returns[-20:]) * np.sqrt(252) * 100  # Annualized in percentage
        indicators['hist_vol_20d'] = float(hist_vol) if not np.isnan(hist_vol) else 20.0
        
        return indicators
    
    def _compute_volume(self, close: np.ndarray, high: np.ndarray, low: np.ndarray, 
                       volume: np.ndarray, df: pd.DataFrame) -> Dict[str, float]:
        """Compute volume indicators."""
        indicators = {}
        
        # OBV (On-Balance Volume)
        obv = talib.OBV(close, volume)
        indicators['obv'] = float(obv[-1]) if not np.isnan(obv[-1]) else 0.0
        indicators['obv_change'] = float((obv[-1] - obv[-2]) / abs(obv[-2]) * 100) if obv[-2] != 0 else 0.0
        
        # AD Line (Accumulation/Distribution Line)
        ad = talib.AD(high, low, close, volume)
        indicators['ad_line'] = float(ad[-1]) if not np.isnan(ad[-1]) else 0.0
        
        # Chaikin Money Flow (CMF)
        adosc = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
        indicators['cmf'] = float(adosc[-1]) if not np.isnan(adosc[-1]) else 0.0
        
        # Money Flow Index (MFI)
        mfi = talib.MFI(high, low, close, volume, timeperiod=14)
        indicators['mfi_14'] = float(mfi[-1]) if not np.isnan(mfi[-1]) else 50.0
        
        # VWAP (Volume Weighted Average Price) - requires intraday data
        # For daily data, we compute a rolling approximation
        typical_price = (high + low + close) / 3
        vwap = np.sum(typical_price[-20:] * volume[-20:]) / np.sum(volume[-20:])
        indicators['vwap_20'] = float(vwap) if not np.isnan(vwap) else float(close[-1])
        indicators['price_vs_vwap'] = float((close[-1] - vwap) / vwap * 100) if not np.isnan(vwap) else 0.0
        
        # Volume ratios
        volume_sma_20 = talib.SMA(volume, timeperiod=20)
        indicators['volume'] = float(volume[-1])
        indicators['volume_sma_20'] = float(volume_sma_20[-1]) if not np.isnan(volume_sma_20[-1]) else float(volume[-1])
        indicators['volume_ratio'] = float(volume[-1] / volume_sma_20[-1]) if not np.isnan(volume_sma_20[-1]) and volume_sma_20[-1] > 0 else 1.0
        
        return indicators
    
    def compute_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
        """
        Identify support and resistance levels using pivot points.
        
        Args:
            df: DataFrame with OHLCV data
            window: Lookback window for pivot detection
        
        Returns:
            Dictionary with support/resistance levels
        """
        if len(df) < window:
            return {'support': [], 'resistance': []}
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local maxima (resistance)
        resistance_levels = []
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                resistance_levels.append(float(highs[i]))
        
        # Find local minima (support)
        support_levels = []
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window+1]):
                support_levels.append(float(lows[i]))
        
        # Get top 3 most recent levels
        support_levels = sorted(support_levels, reverse=True)[:3]
        resistance_levels = sorted(resistance_levels)[:3]
        
        return {
            'support': support_levels,
            'resistance': resistance_levels,
            'current_price': float(df['close'].iloc[-1])
        }


# Singleton instance
technical_indicators = TechnicalIndicators()
