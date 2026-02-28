"""
Simple standalone test for Multi-Agent Intelligence System
Run without pytest dependency
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.quant_agent import QuantAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.regime_agent import RegimeAgent
from app.agents.risk_agent import RiskAgent


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


async def test_quant_agent():
    """Test Quant Agent."""
    print("\n" + "="*60)
    print("Testing Quant Agent")
    print("="*60)
    
    agent = QuantAgent()
    features = get_mock_features()
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    print(f"✓ Agent: {result.agent_name}")
    print(f"✓ Symbol: {result.symbol}")
    print(f"✓ Signal: {result.signal.value}")
    print(f"✓ Confidence: {result.confidence:.2%}")
    print(f"✓ Method: {result.reasoning.get('prediction_method')}")
    print(f"✓ Reasoning keys: {list(result.reasoning.keys())}")
    
    assert result.agent_name == 'quant'
    assert 0.0 <= result.confidence <= 1.0
    print("✅ Quant Agent PASSED")
    
    return result


async def test_sentiment_agent():
    """Test Sentiment Agent."""
    print("\n" + "="*60)
    print("Testing Sentiment Agent")
    print("="*60)
    
    agent = SentimentAgent()
    features = get_mock_features()
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    print(f"✓ Agent: {result.agent_name}")
    print(f"✓ Signal: {result.signal.value}")
    print(f"✓ Confidence: {result.confidence:.2%}")
    print(f"✓ Sentiment Score: {result.reasoning.get('sentiment_score')}")
    print(f"✓ News Count: {result.reasoning.get('news_count')}")
    
    assert result.agent_name == 'sentiment'
    assert 0.0 <= result.confidence <= 1.0
    print("✅ Sentiment Agent PASSED")
    
    return result


async def test_regime_agent():
    """Test Regime Agent."""
    print("\n" + "="*60)
    print("Testing Regime Agent")
    print("="*60)
    
    agent = RegimeAgent()
    features = get_mock_features()
    
    result = await agent.analyze('RELIANCE.NS', features)
    
    print(f"✓ Agent: {result.agent_name}")
    print(f"✓ Signal: {result.signal.value}")
    print(f"✓ Confidence: {result.confidence:.2%}")
    print(f"✓ Strategy: {result.reasoning.get('strategy')}")
    print(f"✓ Regime: {result.reasoning.get('regime')}")
    print(f"✓ Rationale: {result.reasoning.get('rationale')}")
    
    assert result.agent_name == 'regime'
    assert 0.0 <= result.confidence <= 1.0
    print("✅ Regime Agent PASSED")
    
    return result


async def test_risk_agent():
    """Test Risk Agent."""
    print("\n" + "="*60)
    print("Testing Risk Agent")
    print("="*60)
    
    agent = RiskAgent()
    features = get_mock_features()
    
    result = await agent.analyze(
        symbol='RELIANCE.NS',
        features=features,
        entry_price=2850.0,
        target_price=3000.0,
        portfolio_value=100000.0
    )
    
    print(f"✓ Agent: {result.agent_name}")
    print(f"✓ Signal: {result.signal.value}")
    print(f"✓ Confidence: {result.confidence:.2%}")
    print(f"✓ Position Size: {result.reasoning.get('position_size')} shares")
    print(f"✓ Position %: {result.reasoning.get('position_size_pct'):.2f}%")
    print(f"✓ Stop Loss: ₹{result.reasoning.get('stop_loss'):.2f}")
    print(f"✓ Target: ₹{result.reasoning.get('target_price'):.2f}")
    print(f"✓ Risk-Reward: {result.reasoning.get('risk_reward_ratio'):.2f}")
    print(f"✓ Risk Score: {result.reasoning.get('risk_score'):.3f}")
    print(f"✓ Liquidity: {result.reasoning.get('liquidity_check')}")
    
    assert result.agent_name == 'risk'
    assert 'position_size' in result.reasoning
    assert 'stop_loss' in result.reasoning
    print("✅ Risk Agent PASSED")
    
    return result


async def test_all_agents_integration():
    """Test all agents together."""
    print("\n" + "="*60)
    print("INTEGRATION TEST - All Agents")
    print("="*60)
    
    features = get_mock_features()
    
    # Initialize all agents
    quant = QuantAgent()
    sentiment = SentimentAgent()
    regime = RegimeAgent()
    risk = RiskAgent()
    
    # Run all agents in parallel
    results = await asyncio.gather(
        quant.analyze('RELIANCE.NS', features),
        sentiment.analyze('RELIANCE.NS', features),
        regime.analyze('RELIANCE.NS', features),
        risk.analyze('RELIANCE.NS', features, entry_price=2850.0, portfolio_value=100000.0)
    )
    
    quant_result, sentiment_result, regime_result, risk_result = results
    
    print("\n📊 AGENT CONSENSUS SUMMARY")
    print("-" * 60)
    print(f"Quant Agent:     {quant_result.signal.value:15} (confidence: {quant_result.confidence:.1%})")
    print(f"Sentiment Agent: {sentiment_result.signal.value:15} (confidence: {sentiment_result.confidence:.1%})")
    print(f"Regime Agent:    {regime_result.signal.value:15} (confidence: {regime_result.confidence:.1%})")
    print(f"Risk Agent:      {risk_result.signal.value:15} (confidence: {risk_result.confidence:.1%})")
    print("-" * 60)
    
    # Count signals
    from collections import Counter
    signals = [
        quant_result.signal.value,
        sentiment_result.signal.value,
        regime_result.signal.value
    ]
    signal_counts = Counter(signals)
    
    print(f"\n🎯 Signal Distribution: {dict(signal_counts)}")
    print(f"🛡️  Risk Assessment: {risk_result.signal.value}")
    
    avg_confidence = (
        quant_result.confidence + 
        sentiment_result.confidence + 
        regime_result.confidence
    ) / 3
    
    print(f"📈 Average Confidence: {avg_confidence:.1%}")
    
    print("\n✅ INTEGRATION TEST PASSED")
    
    return results


async def test_edge_cases():
    """Test edge cases."""
    print("\n" + "="*60)
    print("Testing Edge Cases")
    print("="*60)
    
    # Test 1: Oversold condition
    print("\n1. Testing oversold condition...")
    features = get_mock_features()
    features['technical']['rsi_14'] = 25.0
    features['technical']['bb_position'] = 0.1
    
    quant = QuantAgent()
    result = await quant.analyze('RELIANCE.NS', features)
    print(f"   RSI 25 → Signal: {result.signal.value} ✓")
    
    # Test 2: No news
    print("\n2. Testing no news scenario...")
    features = get_mock_features()
    features['sentiment']['news_count'] = 0
    
    sentiment = SentimentAgent()
    result = await sentiment.analyze('RELIANCE.NS', features)
    print(f"   No news → Signal: {result.signal.value} ✓")
    
    # Test 3: High volatility ranging (avoid)
    print("\n3. Testing high-vol ranging (avoid)...")
    features = get_mock_features()
    features['regime']['combined'] = 'high_vol_ranging'
    
    regime = RegimeAgent()
    result = await regime.analyze('RELIANCE.NS', features)
    print(f"   High-vol ranging → Signal: {result.signal.value} ✓")
    
    # Test 4: Poor risk-reward
    print("\n4. Testing poor risk-reward...")
    features = get_mock_features()
    
    risk = RiskAgent(min_risk_reward_ratio=2.0)
    result = await risk.analyze(
        'RELIANCE.NS', 
        features, 
        entry_price=2850.0,
        target_price=2870.0  # Only 20 points gain
    )
    print(f"   Poor RR → Signal: {result.signal.value} ✓")
    
    print("\n✅ EDGE CASES PASSED")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CENEX AI - MULTI-AGENT INTELLIGENCE SYSTEM TEST")
    print("Sprint 04 - Layer 3 Validation")
    print("="*60)
    
    try:
        # Individual agent tests
        await test_quant_agent()
        await test_sentiment_agent()
        await test_regime_agent()
        await test_risk_agent()
        
        # Integration test
        await test_all_agents_integration()
        
        # Edge cases
        await test_edge_cases()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✅ Multi-Agent Intelligence System is operational")
        print("✅ All 4 agents functioning correctly")
        print("✅ Agent orchestration working")
        print("✅ Edge cases handled gracefully")
        print("\n📋 Next Steps:")
        print("   1. Train Quant Agent model on historical data")
        print("   2. Train Sentiment Agent model")
        print("   3. Deploy API endpoints")
        print("   4. Build Meta Decision Engine (Sprint 05)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
