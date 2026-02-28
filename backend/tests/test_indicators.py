"""
Unit tests for technical indicators service.
Tests indicator calculations against known reference values.
"""

import pytest
import pandas as pd
import numpy as np
from app.services.indicators import technical_indicators


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    
    # Generate 100 days of realistic price data
    n = 100
    base_price = 100.0
    
    data = {
        'time': pd.date_range(start='2024-01-01', periods=n, freq='D'),
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': []
    }
    
    price = base_price
    for i in range(n):
        daily_return = np.random.normal(0.001, 0.02)  # 0.1% mean, 2% std
        price = price * (1 + daily_return)
        
        open_price = price * (1 + np.random.uniform(-0.005, 0.005))
        high_price = price * (1 + np.random.uniform(0.005, 0.02))
        low_price = price * (1 - np.random.uniform(0.005, 0.02))
        close_price = price
        volume = int(np.random.uniform(1000000, 5000000))
        
        data['open'].append(open_price)
        data['high'].append(high_price)
        data['low'].append(low_price)
        data['close'].append(close_price)
        data['volume'].append(volume)
    
    df = pd.DataFrame(data)
    return df


class TestTechnicalIndicators:
    """Test suite for technical indicators."""
    
    def test_compute_all_returns_dict(self, sample_ohlcv_data):
        """Test that compute_all returns a dictionary."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_compute_all_has_required_indicators(self, sample_ohlcv_data):
        """Test that all required indicators are computed."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        
        # Momentum indicators
        assert 'rsi_14' in result
        assert 'stoch_k' in result
        assert 'stoch_d' in result
        assert 'roc_10' in result
        assert 'willr_14' in result
        
        # Trend indicators
        assert 'macd' in result
        assert 'macd_signal' in result
        assert 'macd_hist' in result
        assert 'adx_14' in result
        assert 'sma_20' in result
        assert 'sma_50' in result
        
        # Volatility indicators
        assert 'bb_upper' in result
        assert 'bb_middle' in result
        assert 'bb_lower' in result
        assert 'atr_14' in result
        
        # Volume indicators
        assert 'obv' in result
        assert 'vwap_20' in result
        assert 'volume_ratio' in result
    
    def test_rsi_range(self, sample_ohlcv_data):
        """Test that RSI is within valid range (0-100)."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert 0 <= result['rsi_14'] <= 100
    
    def test_stochastic_range(self, sample_ohlcv_data):
        """Test that Stochastic is within valid range (0-100)."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert 0 <= result['stoch_k'] <= 100
        assert 0 <= result['stoch_d'] <= 100
    
    def test_bollinger_bands_order(self, sample_ohlcv_data):
        """Test that Bollinger Bands are in correct order (upper > middle > lower)."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert result['bb_upper'] > result['bb_middle']
        assert result['bb_middle'] > result['bb_lower']
    
    def test_atr_positive(self, sample_ohlcv_data):
        """Test that ATR is always positive."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert result['atr_14'] > 0
    
    def test_volume_indicators_computed(self, sample_ohlcv_data):
        """Test that volume indicators are computed."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        assert result['volume'] > 0
        assert result['volume_ratio'] > 0
    
    def test_insufficient_data_raises_error(self):
        """Test that insufficient data raises ValueError."""
        df = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000, 1100]
        })
        
        with pytest.raises(ValueError, match="Insufficient data"):
            technical_indicators.compute_all(df)
    
    def test_missing_column_raises_error(self, sample_ohlcv_data):
        """Test that missing required column raises ValueError."""
        df = sample_ohlcv_data.drop(columns=['volume'])
        
        with pytest.raises(ValueError, match="Missing required column"):
            technical_indicators.compute_all(df)
    
    def test_support_resistance_detection(self, sample_ohlcv_data):
        """Test support and resistance level detection."""
        result = technical_indicators.compute_support_resistance(sample_ohlcv_data, window=20)
        
        assert 'support' in result
        assert 'resistance' in result
        assert 'current_price' in result
        
        assert isinstance(result['support'], list)
        assert isinstance(result['resistance'], list)
        assert len(result['support']) <= 3
        assert len(result['resistance']) <= 3


class TestIndicatorCalculations:
    """Test specific indicator calculations against known values."""
    
    def test_simple_moving_average(self):
        """Test SMA calculation with known values."""
        df = pd.DataFrame({
            'open': [100] * 50,
            'high': [105] * 50,
            'low': [95] * 50,
            'close': [100, 102, 104, 103, 105] + [100] * 45,
            'volume': [1000000] * 50
        })
        
        result = technical_indicators.compute_all(df)
        
        # SMA(20) of last 20 values should be close to 100
        assert abs(result['sma_20'] - 100) < 5
    
    def test_rsi_extreme_values(self):
        """Test RSI with trending data."""
        # Strong uptrend should give high RSI
        uptrend = pd.DataFrame({
            'open': range(100, 150),
            'high': range(105, 155),
            'low': range(95, 145),
            'close': range(100, 150),
            'volume': [1000000] * 50
        })
        
        result = technical_indicators.compute_all(uptrend)
        assert result['rsi_14'] > 60  # Should be overbought
    
    def test_macd_crossover(self, sample_ohlcv_data):
        """Test MACD calculation."""
        result = technical_indicators.compute_all(sample_ohlcv_data)
        
        # MACD histogram should be MACD - Signal
        expected_hist = result['macd'] - result['macd_signal']
        assert abs(result['macd_hist'] - expected_hist) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
