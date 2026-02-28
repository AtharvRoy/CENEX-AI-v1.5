"""
Unit tests for regime detection service.
"""

import pytest
import pandas as pd
import numpy as np
from app.services.regime import regime_detection


@pytest.fixture
def sample_market_data():
    """Generate sample market data with different regimes."""
    np.random.seed(42)
    n = 150
    
    data = {
        'time': pd.date_range(start='2024-01-01', periods=n, freq='D'),
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': []
    }
    
    price = 100.0
    for i in range(n):
        # Create different volatility regimes
        if i < 50:
            vol = 0.01  # Low volatility
        elif i < 100:
            vol = 0.03  # High volatility
        else:
            vol = 0.02  # Medium volatility
        
        daily_return = np.random.normal(0.001, vol)
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


@pytest.fixture
def trending_data():
    """Generate strongly trending data."""
    n = 150
    data = {
        'open': range(100, 100 + n),
        'high': range(105, 105 + n),
        'low': range(95, 95 + n),
        'close': range(100, 100 + n),
        'volume': [1000000] * n
    }
    
    df = pd.DataFrame(data)
    df['time'] = pd.date_range(start='2024-01-01', periods=n, freq='D')
    return df


@pytest.fixture
def ranging_data():
    """Generate ranging (sideways) data."""
    np.random.seed(42)
    n = 150
    
    data = {
        'open': [100 + np.random.uniform(-2, 2) for _ in range(n)],
        'high': [102 + np.random.uniform(0, 2) for _ in range(n)],
        'low': [98 - np.random.uniform(0, 2) for _ in range(n)],
        'close': [100 + np.random.uniform(-2, 2) for _ in range(n)],
        'volume': [1000000] * n
    }
    
    df = pd.DataFrame(data)
    df['time'] = pd.date_range(start='2024-01-01', periods=n, freq='D')
    return df


class TestRegimeDetection:
    """Test suite for regime detection."""
    
    def test_detect_regime_returns_dict(self, sample_market_data):
        """Test that detect_regime returns a dictionary."""
        result = regime_detection.detect_regime(sample_market_data)
        assert isinstance(result, dict)
    
    def test_detect_regime_has_required_fields(self, sample_market_data):
        """Test that regime detection returns all required fields."""
        result = regime_detection.detect_regime(sample_market_data)
        
        assert 'volatility' in result
        assert 'volatility_percentile' in result
        assert 'trend' in result
        assert 'trend_strength' in result
        assert 'combined' in result
        assert 'confidence' in result
    
    def test_volatility_regime_classification(self, sample_market_data):
        """Test that volatility regime is correctly classified."""
        result = regime_detection.detect_regime(sample_market_data)
        
        assert result['volatility'] in ['low_vol', 'medium_vol', 'high_vol']
        assert 0 <= result['volatility_percentile'] <= 1
    
    def test_trend_regime_classification(self, sample_market_data):
        """Test that trend regime is correctly classified."""
        result = regime_detection.detect_regime(sample_market_data)
        
        assert result['trend'] in ['trending_up', 'trending_down', 'trending', 'ranging']
        assert result['trend_strength'] >= 0
    
    def test_combined_regime_format(self, sample_market_data):
        """Test that combined regime has correct format."""
        result = regime_detection.detect_regime(sample_market_data)
        
        # Combined should be "{volatility}_{trend}"
        vol = result['volatility']
        trend = result['trend']
        expected = f"{vol}_{trend}"
        
        assert result['combined'] == expected
    
    def test_confidence_range(self, sample_market_data):
        """Test that confidence is within valid range."""
        result = regime_detection.detect_regime(sample_market_data)
        assert 0 <= result['confidence'] <= 1
    
    def test_trending_data_detection(self, trending_data):
        """Test that strong trends are detected."""
        result = regime_detection.detect_regime(trending_data)
        
        # Should detect trending regime with high ADX
        assert 'trending' in result['trend']
        assert result['trend_strength'] > 20  # ADX should be strong
    
    def test_ranging_data_detection(self, ranging_data):
        """Test that ranging markets are detected."""
        result = regime_detection.detect_regime(ranging_data)
        
        # Should detect ranging regime with low ADX
        assert result['trend'] == 'ranging' or result['trend_strength'] < 25
    
    def test_insufficient_data_raises_error(self):
        """Test that insufficient data raises ValueError."""
        df = pd.DataFrame({
            'open': [100] * 50,
            'high': [105] * 50,
            'low': [95] * 50,
            'close': [100] * 50,
            'volume': [1000000] * 50
        })
        
        with pytest.raises(ValueError, match="Insufficient data"):
            regime_detection.detect_regime(df)


class TestHMMTraining:
    """Test suite for Hidden Markov Model training."""
    
    def test_hmm_training_with_sufficient_data(self, sample_market_data):
        """Test HMM training with sufficient data."""
        # Need to generate more data for HMM (500+ points)
        np.random.seed(42)
        n = 600
        
        data = {
            'open': [100 + i*0.1 + np.random.uniform(-1, 1) for i in range(n)],
            'high': [102 + i*0.1 + np.random.uniform(0, 1) for i in range(n)],
            'low': [98 + i*0.1 - np.random.uniform(0, 1) for i in range(n)],
            'close': [100 + i*0.1 + np.random.uniform(-1, 1) for i in range(n)],
            'volume': [1000000] * n
        }
        
        df = pd.DataFrame(data)
        
        result = regime_detection.train_hmm(df, n_states=3)
        
        assert result['trained'] is True
        assert result['n_states'] == 3
        assert result['data_points'] >= 500
        assert 'state_stats' in result
        assert 'aic' in result
        assert 'bic' in result
    
    def test_hmm_insufficient_data_raises_error(self):
        """Test that HMM training with insufficient data raises error."""
        df = pd.DataFrame({
            'open': [100] * 100,
            'high': [105] * 100,
            'low': [95] * 100,
            'close': [100] * 100,
            'volume': [1000000] * 100
        })
        
        with pytest.raises(ValueError, match="Insufficient data"):
            regime_detection.train_hmm(df, n_states=3)
    
    def test_hmm_state_stats(self, sample_market_data):
        """Test that HMM returns state statistics."""
        # Generate sufficient data
        np.random.seed(42)
        n = 600
        
        data = {
            'open': [100 + i*0.05 + np.random.uniform(-2, 2) for i in range(n)],
            'high': [102 + i*0.05 + np.random.uniform(0, 2) for i in range(n)],
            'low': [98 + i*0.05 - np.random.uniform(0, 2) for i in range(n)],
            'close': [100 + i*0.05 + np.random.uniform(-2, 2) for i in range(n)],
            'volume': [1000000] * n
        }
        
        df = pd.DataFrame(data)
        
        result = regime_detection.train_hmm(df, n_states=3)
        
        state_stats = result['state_stats']
        assert len(state_stats) == 3
        
        for state_name, stats in state_stats.items():
            assert 'count' in stats
            assert 'mean_return' in stats
            assert 'volatility' in stats
            assert 'sharpe' in stats


class TestRegimeStats:
    """Test regime statistics calculation."""
    
    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        # Create data with known drawdown
        prices = np.array([100, 110, 105, 95, 100])  # Max drawdown from 110 to 95 = -13.6%
        
        drawdown = regime_detection._calculate_max_drawdown(prices)
        
        # Expected drawdown: (95 - 110) / 110 = -0.136
        assert abs(drawdown - (-0.136)) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
