"""
Test suite for Multi-Agent Intelligence System
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.agents.base_agent import AgentOutput, SignalType
from app.agents.quant_agent import QuantAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.regime_agent import RegimeAgent
from app.agents.risk_agent import RiskAgent


# Mock Features

def get_mock_features():
    """Generate mock feature data for testing."""
    return {
        'symbol': 'RELIANCE.NS',
        'price': {
            'close': 2850.0,
            'open': 2840.0,
            'high': 2860.0,
            'low': 2835.0,
            'volume': 5000000,
        },
        'technical': {
            'rsi_14': 65.0,
            'rsi_28': 58.0,
            'macd': 15.0,
            'macd_signal': 12.0,
            'macd_hist': 3.0,
            'adx_14': 28.0,
            'bb_upper': 2900.0,
            'bb_middle': 2850.0,
            'bb_lower': 2800.0,
            'bb_width': 100.0,
            'bb_position': 0.5,
            'atr_14': 50.0,
            'obv_pct': 0.05,
            'vwap_distance': 0.01,
            'volume_sma_ratio': 1.2,
            'returns_5d': 0.03,
            'returns_20d': 0.08,
            'volatility_20d': 0.025,
            'momentum_10d': 0.04,
        },
        'regime': {
            'combined': 'high_vol_trending',
            'volatility': 'high',
            'trend': 'strong_up',
            'confidence': 0.8,
        },
        'sentiment': {
            'sentiment_score': 0.35,
            'sentiment_label': 'positive',
            'news_count': 8,
            'freshness_hours': 12,
        }
    }


# Test Quant Agent

@pytest.mark.asyncio
async def test_quant_agent_rule_based():
    """Test Quant Agent with rule-based fallback."""
    agent = QuantAgent()
    features = get_mock_features()
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert isinstance(result, AgentOutput)
    assert result.agent_name == 'quant'
    assert result.symbol == 'RELIANCE.NS'
    assert result.signal in [s for s in SignalType]
    assert 0.0 <= result.confidence <= 1.0
    assert 'prediction_method' in result.reasoning
    assert result.reasoning['prediction_method'] == 'rule_based'


@pytest.mark.asyncio
async def test_quant_agent_oversold():
    """Test Quant Agent detects oversold condition."""
    agent = QuantAgent()
    features = get_mock_features()
    
    # Set oversold conditions
    features['technical']['rsi_14'] = 25.0
    features['technical']['bb_position'] = 0.1
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    # Should generate BUY signal
    assert result.signal in [SignalType.BUY, SignalType.STRONG_BUY]


@pytest.mark.asyncio
async def test_quant_agent_overbought():
    """Test Quant Agent detects overbought condition."""
    agent = QuantAgent()
    features = get_mock_features()
    
    # Set overbought conditions
    features['technical']['rsi_14'] = 75.0
    features['technical']['macd_hist'] = -8.0
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    # Should generate SELL signal or HOLD
    assert result.signal in [SignalType.SELL, SignalType.STRONG_SELL, SignalType.HOLD]


# Test Sentiment Agent

@pytest.mark.asyncio
async def test_sentiment_agent_positive():
    """Test Sentiment Agent with positive sentiment."""
    agent = SentimentAgent()
    features = get_mock_features()
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.agent_name == 'sentiment'
    assert result.signal in [SignalType.BUY, SignalType.STRONG_BUY]
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_sentiment_agent_negative():
    """Test Sentiment Agent with negative sentiment."""
    agent = SentimentAgent()
    features = get_mock_features()
    
    # Set negative sentiment
    features['sentiment']['sentiment_score'] = -0.45
    features['sentiment']['sentiment_label'] = 'negative'
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.signal in [SignalType.SELL, SignalType.STRONG_SELL]


@pytest.mark.asyncio
async def test_sentiment_agent_no_news():
    """Test Sentiment Agent with no news data."""
    agent = SentimentAgent()
    features = get_mock_features()
    
    # No news
    features['sentiment']['news_count'] = 0
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.signal == SignalType.NO_SIGNAL
    assert 'No news available' in result.reasoning['reason']


# Test Regime Agent

@pytest.mark.asyncio
async def test_regime_agent_trend_following():
    """Test Regime Agent trend-following strategy."""
    agent = RegimeAgent()
    features = get_mock_features()
    
    # High-vol trending regime
    features['regime']['combined'] = 'high_vol_trending'
    features['technical']['macd_hist'] = 8.0
    features['technical']['adx_14'] = 35.0
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.agent_name == 'regime'
    assert result.signal == SignalType.BUY
    assert 'trend_following' in result.reasoning['strategy']


@pytest.mark.asyncio
async def test_regime_agent_mean_reversion():
    """Test Regime Agent mean reversion strategy."""
    agent = RegimeAgent()
    features = get_mock_features()
    
    # Low-vol ranging regime
    features['regime']['combined'] = 'low_vol_ranging'
    features['technical']['rsi_14'] = 28.0
    features['technical']['bb_position'] = 0.15
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.signal == SignalType.BUY
    assert 'mean_reversion' in result.reasoning['strategy']


@pytest.mark.asyncio
async def test_regime_agent_avoid():
    """Test Regime Agent avoids high-vol ranging market."""
    agent = RegimeAgent()
    features = get_mock_features()
    
    # High-vol ranging - unfavorable conditions
    features['regime']['combined'] = 'high_vol_ranging'
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    assert result.signal == SignalType.NO_SIGNAL
    assert 'avoid' in result.reasoning['strategy']


# Test Risk Agent

@pytest.mark.asyncio
async def test_risk_agent_approve():
    """Test Risk Agent approves reasonable trade."""
    agent = RiskAgent()
    features = get_mock_features()
    
    result = await agent.analyze(
        symbol='RELIANCE.NS',
        features=features,
        entry_price=2850.0,
        target_price=3000.0,
        portfolio_value=100000.0
    )
    
    assert result.agent_name == 'risk'
    assert result.signal == SignalType.APPROVE
    assert 'position_size' in result.reasoning
    assert 'stop_loss' in result.reasoning
    assert 'risk_reward_ratio' in result.reasoning


@pytest.mark.asyncio
async def test_risk_agent_position_sizing():
    """Test Risk Agent position sizing calculation."""
    agent = RiskAgent(
        max_position_size_pct=10.0,
        max_risk_per_trade_pct=2.0
    )
    features = get_mock_features()
    
    result = await agent.analyze(
        symbol='RELIANCE.NS',
        features=features,
        entry_price=2850.0,
        portfolio_value=100000.0
    )
    
    # Position should be reasonable
    position_size_pct = result.reasoning['position_size_pct']
    assert 0 < position_size_pct <= 10.0
    
    # Risk-reward should be acceptable
    rr_ratio = result.reasoning['risk_reward_ratio']
    assert rr_ratio >= 1.5


@pytest.mark.asyncio
async def test_risk_agent_reject_poor_rr():
    """Test Risk Agent rejects poor risk-reward ratio."""
    agent = RiskAgent(min_risk_reward_ratio=2.0)
    features = get_mock_features()
    
    # Set very close target (poor RR)
    result = await agent.analyze(
        symbol='RELIANCE.NS',
        features=features,
        entry_price=2850.0,
        target_price=2870.0,  # Only 20 points up, stop at 2750 (100 down)
        portfolio_value=100000.0
    )
    
    # Should reject due to poor risk-reward
    assert result.signal == SignalType.REJECT


@pytest.mark.asyncio
async def test_risk_agent_high_volatility():
    """Test Risk Agent adjusts for high volatility."""
    agent = RiskAgent()
    features = get_mock_features()
    
    # Set high volatility
    features['technical']['volatility_20d'] = 0.08  # 8% daily volatility
    
    result = await agent.analyze(
        symbol='RELIANCE.NS',
        features=features,
        entry_price=2850.0,
        portfolio_value=100000.0
    )
    
    # Should have high volatility warning
    assert result.reasoning.get('volatility_warning') is not None


# Test Agent Info

def test_agent_info():
    """Test agent metadata retrieval."""
    agent = QuantAgent()
    info = agent.get_info()
    
    assert 'name' in info
    assert 'version' in info
    assert 'model_loaded' in info
    assert info['name'] == 'quant'


# Test Base Agent Validation

def test_feature_validation():
    """Test feature validation method."""
    agent = QuantAgent()
    
    # Valid features
    features = {'technical': {}, 'price': {}}
    assert agent._validate_features(features, ['technical', 'price'])
    
    # Missing feature
    assert not agent._validate_features(features, ['technical', 'sentiment'])


# Integration Test

@pytest.mark.asyncio
async def test_all_agents_integration():
    """Test all agents work together."""
    features = get_mock_features()
    
    # Initialize all agents
    quant = QuantAgent()
    sentiment = SentimentAgent()
    regime = RegimeAgent()
    risk = RiskAgent()
    
    # Run all agents
    quant_result = await quant.analyze('RELIANCE.NS', features)
    sentiment_result = await sentiment.analyze('RELIANCE.NS', features)
    regime_result = await regime.analyze('RELIANCE.NS', features)
    risk_result = await risk.analyze(
        'RELIANCE.NS', 
        features, 
        entry_price=2850.0,
        portfolio_value=100000.0
    )
    
    # All should return valid outputs
    assert all(isinstance(r, AgentOutput) for r in [
        quant_result, sentiment_result, regime_result, risk_result
    ])
    
    # All should have reasoning
    assert all(r.reasoning for r in [
        quant_result, sentiment_result, regime_result, risk_result
    ])
    
    print("\n=== Integration Test Results ===")
    print(f"Quant: {quant_result.signal.value} (confidence: {quant_result.confidence:.2f})")
    print(f"Sentiment: {sentiment_result.signal.value} (confidence: {sentiment_result.confidence:.2f})")
    print(f"Regime: {regime_result.signal.value} (confidence: {regime_result.confidence:.2f})")
    print(f"Risk: {risk_result.signal.value} (confidence: {risk_result.confidence:.2f})")


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_all_agents_integration())
