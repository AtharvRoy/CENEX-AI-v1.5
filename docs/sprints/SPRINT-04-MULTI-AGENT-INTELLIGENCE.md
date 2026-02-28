# Sprint 04: Multi-Agent Intelligence (Layer 3)

**Duration:** Week 7-8  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 03 (Feature Factory)

## Goals

Build the Multi-Agent Intelligence system - 4 specialized AI agents that analyze market conditions from different perspectives:

1. **🧮 Quant Agent** - Statistical signals, mean reversion, momentum
2. **📰 Sentiment Agent** - News-driven sentiment analysis
3. **🌍 Regime Agent** - Market regime classification and regime-specific strategies
4. **⚠️ Risk Agent** - Position sizing, stop-loss, risk-reward validation

Each agent outputs a prediction + confidence. Layer 4 (Meta Decision Engine) will ensemble them.

## Deliverables

### 1. Agent Base Class
- `backend/app/agents/base_agent.py`
  - Abstract base class for all agents
  - Standard interface: `analyze(symbol, features) → AgentOutput`
  - AgentOutput schema: `{signal: str, confidence: float, reasoning: dict}`

### 2. Quant Agent
- `backend/app/agents/quant_agent.py`
  - **Model:** LightGBM classifier (5 classes: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
  - **Features:** Technical indicators (RSI, MACD, ADX, Bollinger, etc.)
  - **Training data:** Historical OHLCV + labels (future returns)
  - **Strategy:** Quantitative patterns, breakouts, momentum
  - **Output:** Signal + confidence + feature importance

### 3. Sentiment Agent
- `backend/app/agents/sentiment_agent.py`
  - **Model:** Logistic Regression (sentiment → signal mapping)
  - **Features:** FinBERT sentiment score, news volume, sentiment trend
  - **Logic:** 
    - Sentiment > 0.3 + rising → BUY signal
    - Sentiment < -0.3 + falling → SELL signal
    - Confidence based on news freshness and volume
  - **Output:** Signal + confidence + news summary

### 4. Regime Agent
- `backend/app/agents/regime_agent.py`
  - **Model:** Regime-specific strategy rules
  - **Logic:**
    - High-vol trending → Trend-following (MACD, ADX)
    - Low-vol ranging → Mean reversion (RSI, Bollinger)
    - High-vol ranging → Avoid (NO_SIGNAL)
  - **Output:** Signal + confidence + regime context

### 5. Risk Agent
- `backend/app/agents/risk_agent.py`
  - **Model:** Risk assessment (not a signal generator)
  - **Features:** Volatility, drawdown, position size, portfolio exposure
  - **Logic:**
    - Compute position size (Kelly Criterion or fixed %)
    - Validate stop-loss (ATR-based)
    - Check risk-reward ratio (>1.5 required)
    - Liquidity check (average volume)
  - **Output:** Risk score (0-1), suggested position size, stop-loss level

### 6. Agent Orchestration Service
- `backend/app/services/agent_orchestrator.py`
  - Run all 4 agents in parallel
  - Collect outputs
  - Pass to Meta Decision Engine (Layer 4)
  - Log agent outputs for performance tracking

### 7. Model Training Pipeline
- `backend/app/ml/train_quant_agent.py`
  - Fetch historical data + labels (future 5-day returns)
  - Train LightGBM classifier
  - Hyperparameter tuning (Optuna)
  - Save model to `backend/models/quant_agent_v1.pkl`
  
- `backend/app/ml/train_sentiment_agent.py`
  - Historical sentiment + price movements
  - Train logistic regression
  - Save model

### 8. Model Storage
- `backend/models/` directory
  - `quant_agent_v1.pkl` - LightGBM model
  - `sentiment_agent_v1.pkl` - Logistic regression
  - `metadata.json` - model versions, training dates, performance metrics

### 9. API Endpoints
- `POST /api/agents/analyze/{symbol}` - run all agents, return outputs
- `GET /api/agents/{agent_name}/{symbol}` - run single agent
- `POST /api/admin/agents/retrain` - trigger model retraining (admin only)

## Tech Stack

- **ML Models:** LightGBM, XGBoost, scikit-learn (Logistic Regression)
- **Hyperparameter Tuning:** Optuna
- **Model Serving:** Pickle (pickle/joblib)
- **Future:** MLflow for experiment tracking

## Dependencies

```txt
lightgbm>=4.1.0
xgboost>=2.0.0
scikit-learn>=1.3.0
optuna>=3.5.0
joblib>=1.3.0
mlflow>=2.9.0  # Future
```

## Agent Output Schema

```python
from pydantic import BaseModel

class AgentOutput(BaseModel):
    agent_name: str  # "quant", "sentiment", "regime", "risk"
    symbol: str
    signal: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL
    confidence: float  # 0.0 to 1.0
    reasoning: dict  # agent-specific context
    timestamp: datetime

# Example: Quant Agent output
{
    "agent_name": "quant",
    "symbol": "RELIANCE.NS",
    "signal": "BUY",
    "confidence": 0.78,
    "reasoning": {
        "top_features": ["rsi_14", "macd", "adx_14"],
        "feature_importance": {"rsi_14": 0.35, "macd": 0.28, "adx_14": 0.22},
        "model_version": "v1.2",
        "probability_distribution": {
            "STRONG_BUY": 0.15,
            "BUY": 0.63,
            "HOLD": 0.18,
            "SELL": 0.03,
            "STRONG_SELL": 0.01
        }
    },
    "timestamp": "2026-02-28T14:35:00Z"
}

# Example: Risk Agent output
{
    "agent_name": "risk",
    "symbol": "RELIANCE.NS",
    "signal": "APPROVE",  # Risk doesn't generate buy/sell, only approve/reject
    "confidence": 0.85,
    "reasoning": {
        "risk_score": 0.15,  # Low risk = good
        "position_size_pct": 5.0,  # 5% of portfolio
        "stop_loss": 2750,  # ATR-based
        "risk_reward_ratio": 2.3,  # Target: 2900, Stop: 2750, Entry: 2850
        "liquidity_check": "PASS",
        "volatility_percentile": 0.35
    },
    "timestamp": "2026-02-28T14:35:00Z"
}
```

## Labeling Logic (Training Data)

```python
def generate_labels(df, lookahead_days=5):
    """Generate labels for supervised learning."""
    
    # Compute future returns
    df['future_return'] = df['close'].pct_change(lookahead_days).shift(-lookahead_days)
    
    # Label based on magnitude
    def classify_return(ret):
        if ret > 0.05:  # >5% gain
            return "STRONG_BUY"
        elif ret > 0.02:  # 2-5% gain
            return "BUY"
        elif ret > -0.02:  # -2% to +2%
            return "HOLD"
        elif ret > -0.05:  # -5% to -2%
            return "SELL"
        else:  # <-5% loss
            return "STRONG_SELL"
    
    df['label'] = df['future_return'].apply(classify_return)
    return df.dropna()
```

## Quant Agent Training Code (Sample)

```python
import lightgbm as lgb
from sklearn.model_selection import train_test_split

def train_quant_agent(df_features, labels):
    """Train LightGBM classifier for quant agent."""
    
    # Feature columns
    feature_cols = [
        'rsi_14', 'macd', 'macd_signal', 'adx_14',
        'bb_width', 'atr_14', 'obv_pct', 'vwap_distance'
    ]
    
    X = df_features[feature_cols]
    y = labels  # Encoded: 0=STRONG_SELL, 1=SELL, 2=HOLD, 3=BUY, 4=STRONG_BUY
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # LightGBM parameters
    params = {
        'objective': 'multiclass',
        'num_class': 5,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8
    }
    
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[test_data],
        callbacks=[lgb.early_stopping(stopping_rounds=20)]
    )
    
    # Save model
    import joblib
    joblib.dump(model, 'backend/models/quant_agent_v1.pkl')
    
    return model
```

## Performance Targets

- **Agent execution time:** <1 second per agent
- **Model accuracy (Quant):** >55% on test set (better than random 20%)
- **Ensemble accuracy (all agents):** >60% (Layer 4 goal)
- **Risk agent false positive rate:** <10% (avoiding bad trades)

## Testing

- Unit tests: Individual agent logic
- Integration tests: Full agent orchestration
- Backtesting: Historical performance simulation
- A/B testing: Compare agent versions

## Acceptance Criteria

- [ ] All 4 agents run successfully
- [ ] Quant agent model trained and saved
- [ ] Agent outputs follow standard schema
- [ ] Risk agent validates position sizing and stop-loss
- [ ] API endpoints return agent predictions
- [ ] Logging captures agent reasoning for performance analysis

## Next Sprint

**Sprint 05: Meta Decision Engine + Signal Quality (Layers 4 & 5)** - Ensemble agents, confidence calibration, signal filtering

---

**Assigned to:** Sub-agent (multi-agent-intelligence)  
**Start Date:** TBD (after Sprint 03)  
**Target Completion:** TBD  
