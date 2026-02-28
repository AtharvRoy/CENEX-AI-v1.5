# Sprint 05: Meta Decision Engine + Signal Quality (Layers 4 & 5)

**Duration:** Week 9-10  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 04 (Multi-Agent Intelligence)

## Goals

Build the ensemble system that combines all agent outputs into final trading signals, then filters them through quality gates.

**Layer 4:** Meta Decision Engine - Ensemble agent predictions  
**Layer 5:** Signal Quality Engine - Filter low-quality signals

## Deliverables

### 1. Meta Decision Engine (Layer 4)
- `backend/app/services/meta_decision_engine.py`
  - **Ensemble Method:** Logistic regression stacking (meta-learner)
  - **Input:** 4 agent outputs (signal + confidence + reasoning)
  - **Output:** Final signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL)
  - **Confidence Calibration:** Platt scaling for probability calibration

### 2. Signal Quality Engine (Layer 5)
- `backend/app/services/signal_quality_engine.py`
  - **Regime-aware filtering:** Different thresholds per regime
  - **Volatility anomaly detection:** Flag extreme vol spikes
  - **Historical signal decay analysis:** Reduce confidence if similar signals failed recently
  - **Liquidity checks:** Ensure tradeable volume
  - **Quality gate:** Confidence > 80% + Risk OK = PASS

### 3. Ensemble Training Pipeline
- `backend/app/ml/train_meta_learner.py`
  - Collect historical agent outputs
  - Train logistic regression meta-model
  - Cross-validation for ensemble weights
  - Save meta-model to `backend/models/meta_learner_v1.pkl`

### 4. Signal Generation Pipeline (End-to-End)
- `backend/app/services/signal_pipeline.py`
  - Fetch features (Layer 2)
  - Run all agents (Layer 3)
  - Ensemble predictions (Layer 4)
  - Filter through quality gates (Layer 5)
  - Save final signal to database
  - Return signal + full reasoning chain

### 5. API Endpoints
- `POST /api/signals/generate/{symbol}` - generate signal for a symbol
- `GET /api/signals/latest` - list latest signals (all symbols)
- `GET /api/signals/{symbol}` - signal history for a symbol
- `GET /api/signals/{signal_id}` - detailed signal breakdown (all agent outputs)

### 6. Signal Storage & Indexing
- Signals saved to `signals` table (already defined in Sprint 01)
- Agent outputs stored in `reasoning` JSONB field
- Indexes on `symbol`, `created_at`, `confidence` for fast queries

## Tech Stack

- **Meta-learner:** scikit-learn Logistic Regression
- **Calibration:** Platt scaling (CalibratedClassifierCV)
- **Signal filtering:** Rule-based + statistical thresholds

## Dependencies

```txt
scikit-learn>=1.3.0
scipy>=1.11.0
joblib>=1.3.0
```

## Ensemble Logic (Layer 4)

### Input: Agent Outputs
```python
{
    "quant": {"signal": "BUY", "confidence": 0.78},
    "sentiment": {"signal": "BUY", "confidence": 0.65},
    "regime": {"signal": "HOLD", "confidence": 0.82},
    "risk": {"signal": "APPROVE", "confidence": 0.85}
}
```

### Stacking Ensemble
```python
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

def train_meta_learner(agent_predictions, true_outcomes):
    """
    Train meta-learner to ensemble agent predictions.
    
    agent_predictions: shape (n_samples, 4) - encoded agent signals
    true_outcomes: shape (n_samples,) - actual future returns (labels)
    """
    
    # Logistic regression meta-model
    base_model = LogisticRegression(multi_class='multinomial', max_iter=1000)
    
    # Calibrate probabilities using Platt scaling
    meta_model = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)
    
    meta_model.fit(agent_predictions, true_outcomes)
    
    return meta_model

def ensemble_agents(agent_outputs, meta_model):
    """Generate final signal from agent outputs."""
    
    # Encode agent signals to numerical features
    features = encode_agent_outputs(agent_outputs)
    
    # Predict using meta-model
    probabilities = meta_model.predict_proba(features)
    prediction = meta_model.predict(features)[0]
    confidence = probabilities.max()
    
    signal_map = {
        0: "STRONG_SELL",
        1: "SELL",
        2: "HOLD",
        3: "BUY",
        4: "STRONG_BUY"
    }
    
    return {
        "signal": signal_map[prediction],
        "confidence": confidence,
        "probabilities": dict(zip(signal_map.values(), probabilities[0]))
    }
```

## Signal Quality Engine (Layer 5)

### Quality Filters

#### 1. Confidence Threshold (Regime-Aware)
```python
def check_confidence_threshold(signal, regime):
    """Different confidence thresholds per regime."""
    
    thresholds = {
        "high_vol_trending": 0.85,  # Strict (risky regime)
        "low_vol_trending": 0.75,   # Moderate
        "low_vol_ranging": 0.80,    # Moderate-strict (mean reversion)
        "high_vol_ranging": 0.90    # Very strict (avoid)
    }
    
    required_confidence = thresholds.get(regime, 0.80)
    
    return signal["confidence"] >= required_confidence
```

#### 2. Volatility Anomaly Detection
```python
def check_volatility_anomaly(symbol, current_vol, historical_vol):
    """Flag extreme volatility spikes."""
    
    vol_percentile = np.percentile(historical_vol, 95)
    
    if current_vol > 3 * vol_percentile:
        # Extreme volatility spike - reduce confidence or reject
        return False
    
    return True
```

#### 3. Signal Decay Analysis
```python
def check_signal_decay(symbol, signal_type, recent_performance):
    """
    Reduce confidence if similar signals failed recently.
    
    Example: If last 3 BUY signals for RELIANCE.NS were losses,
    reduce confidence or reject new BUY signal.
    """
    
    # Get last 5 signals of same type for this symbol
    recent_signals = recent_performance.filter(
        symbol=symbol,
        signal_type=signal_type
    ).limit(5)
    
    win_rate = recent_signals.filter(outcome="win").count() / len(recent_signals)
    
    if win_rate < 0.4:  # <40% win rate recently
        # Signal is decaying - reduce confidence or reject
        return False
    
    return True
```

#### 4. Liquidity Check
```python
def check_liquidity(symbol, avg_volume, current_volume):
    """Ensure sufficient trading volume."""
    
    # Require at least 50% of average volume
    if current_volume < 0.5 * avg_volume:
        return False
    
    # Require minimum absolute volume (e.g., 100k shares)
    if current_volume < 100_000:
        return False
    
    return True
```

### Final Quality Gate
```python
def signal_quality_gate(signal, symbol, features, recent_performance):
    """
    Run all quality checks. Signal must pass ALL to be published.
    """
    
    checks = {
        "confidence": check_confidence_threshold(signal, features["regime"]),
        "volatility": check_volatility_anomaly(symbol, features["atr"], features["historical_atr"]),
        "decay": check_signal_decay(symbol, signal["signal"], recent_performance),
        "liquidity": check_liquidity(symbol, features["avg_volume"], features["current_volume"]),
        "risk": signal["risk_score"] < 0.3  # Low risk required
    }
    
    passed = all(checks.values())
    
    return {
        "passed": passed,
        "checks": checks,
        "final_signal": signal if passed else {"signal": "NO_SIGNAL", "reason": "quality_gate_failed"}
    }
```

## End-to-End Signal Generation

```python
async def generate_signal(symbol: str):
    """
    Full signal generation pipeline (Layers 2-5).
    """
    
    # Layer 2: Fetch features
    features = await feature_pipeline.compute_features(symbol)
    
    # Layer 3: Run all agents
    agent_outputs = await agent_orchestrator.run_agents(symbol, features)
    
    # Layer 4: Ensemble predictions
    meta_signal = meta_decision_engine.ensemble(agent_outputs)
    
    # Layer 5: Quality filtering
    quality_result = signal_quality_engine.validate(meta_signal, symbol, features)
    
    if quality_result["passed"]:
        # Save to database
        signal = Signal(
            symbol=symbol,
            exchange="NSE",
            signal_type=meta_signal["signal"],
            confidence=meta_signal["confidence"],
            reasoning={
                "agent_outputs": agent_outputs,
                "meta_decision": meta_signal,
                "quality_checks": quality_result["checks"]
            },
            regime=features["regime"]
        )
        await db.save(signal)
        
        return signal
    else:
        return {"signal": "NO_SIGNAL", "reason": quality_result}
```

## Performance Targets

- **Signal generation latency:** <5 seconds (Layers 2-5 combined)
- **Meta-model accuracy:** >60% (better than any single agent)
- **Quality gate pass rate:** 20-30% (filters out 70-80% of weak signals)
- **Final signal win rate:** >65% (only high-quality signals)

## Testing

- Unit tests: Individual quality checks
- Integration tests: Full pipeline (features → agents → ensemble → quality gate)
- Backtesting: Historical signal performance
- A/B testing: Meta-learner vs simple voting

## Acceptance Criteria

- [ ] Meta-learner trained and saved
- [ ] Ensemble combines 4 agents correctly
- [ ] Quality gate filters low-confidence signals
- [ ] End-to-end signal generation works
- [ ] Signals saved to database with full reasoning chain
- [ ] API endpoints return signals + explanations

## Next Sprint

**Sprint 06: Performance Memory (Layer 6)** - Trade outcome tracking, self-learning loop

---

**Assigned to:** Sub-agent (meta-decision-engine)  
**Start Date:** TBD (after Sprint 04)  
**Target Completion:** TBD  
