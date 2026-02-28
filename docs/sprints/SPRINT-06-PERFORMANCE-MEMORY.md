# Sprint 06: Performance Memory (Layer 6 - Self-Learning Loop)

**Duration:** Week 11-12  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 05 (Meta Decision Engine + Signal Quality)

## Goals

Build the self-learning system that tracks signal performance, learns from outcomes, and continuously improves the system. This is the **competitive moat** — proprietary intelligence that gets better over time.

## Deliverables

### 1. Trade Outcome Tracking
- `backend/app/services/performance_tracker.py`
  - Track every signal → trade → outcome
  - Compute PnL%, win/loss, days held
  - Store in `signal_performance` table
  - Regime-specific performance metrics

### 2. Signal Performance Analytics
- `backend/app/services/performance_analytics.py`
  - Win rate by signal type (BUY, SELL, etc.)
  - Win rate by regime (high_vol_trending vs low_vol_ranging)
  - Win rate by agent (which agent is most accurate?)
  - Signal decay detection (are signals getting worse over time?)
  - Feature importance drift (which indicators matter most?)

### 3. Model Retraining Triggers
- `backend/app/services/retraining_service.py`
  - **Auto-trigger retraining when:**
    - Accuracy drops below threshold (e.g., <55%)
    - New data accumulates (e.g., 1000 new signals)
    - Regime shift detected (new market conditions)
  - **Retrain:**
    - Quant agent (LightGBM)
    - Sentiment agent (Logistic Regression)
    - Meta-learner (ensemble model)
  - **A/B test:** New model vs old model before deployment

### 4. Signal Intelligence Database
- `backend/app/services/signal_intelligence.py`
  - Aggregate performance by symbol, regime, agent
  - Build "signal memory" — which signals worked in which regimes
  - Inform future signal generation (adaptive thresholds)

### 5. Performance Dashboard API
- `GET /api/performance/summary` - overall system performance
- `GET /api/performance/signals` - signal-level metrics
- `GET /api/performance/agents` - agent-level accuracy
- `GET /api/performance/regimes` - regime-specific win rates
- `GET /api/performance/symbols/{symbol}` - per-symbol performance

### 6. Celery Tasks (Automated Learning)
- `backend/app/tasks/performance_tasks.py`
  - `update_signal_performance()` - daily task to compute outcomes
  - `check_retraining_triggers()` - weekly check for model drift
  - `retrain_models()` - trigger retraining pipeline

## Tech Stack

- **Analytics:** pandas, numpy, scipy (statistical analysis)
- **Visualization:** Plotly (future - performance charts)
- **Retraining:** Same ML stack as Sprints 03-04

## Database Schema (Already Defined in Sprint 01)

```sql
CREATE TABLE signal_performance (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    symbol VARCHAR(50) NOT NULL,
    regime VARCHAR(50),
    outcome VARCHAR(20), -- win, loss, breakeven, expired
    pnl_percent FLOAT,
    days_held INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Performance Tracking Logic

### 1. Trade Outcome Computation
```python
async def compute_signal_outcome(signal_id: int):
    """
    Compute outcome of a signal after trade is closed.
    """
    
    signal = await db.get_signal(signal_id)
    trade = await db.get_trade_by_signal(signal_id)
    
    if not trade or trade.status != "closed":
        return None  # Trade still open or doesn't exist
    
    # Compute PnL%
    pnl_percent = ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100
    
    # Classify outcome
    if pnl_percent > 2:
        outcome = "win"
    elif pnl_percent < -2:
        outcome = "loss"
    else:
        outcome = "breakeven"
    
    # Days held
    days_held = (trade.closed_at - trade.executed_at).days
    
    # Save performance record
    performance = SignalPerformance(
        signal_id=signal_id,
        symbol=signal.symbol,
        regime=signal.regime,
        outcome=outcome,
        pnl_percent=pnl_percent,
        days_held=days_held
    )
    
    await db.save(performance)
    
    return performance
```

### 2. Signal Decay Detection
```python
def detect_signal_decay(symbol: str, signal_type: str, lookback_days: int = 30):
    """
    Detect if signal quality is degrading over time.
    """
    
    recent_signals = db.query(SignalPerformance).filter(
        SignalPerformance.symbol == symbol,
        SignalPerformance.signal.signal_type == signal_type,
        SignalPerformance.created_at >= datetime.utcnow() - timedelta(days=lookback_days)
    ).all()
    
    if len(recent_signals) < 10:
        return {"decaying": False, "reason": "insufficient_data"}
    
    win_rate = sum(1 for s in recent_signals if s.outcome == "win") / len(recent_signals)
    avg_pnl = sum(s.pnl_percent for s in recent_signals) / len(recent_signals)
    
    # Signal is decaying if win rate < 50% or avg PnL negative
    if win_rate < 0.5 or avg_pnl < 0:
        return {
            "decaying": True,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "recommendation": "reduce_confidence_or_pause"
        }
    
    return {"decaying": False, "win_rate": win_rate, "avg_pnl": avg_pnl}
```

### 3. Agent Performance Analysis
```python
def analyze_agent_performance():
    """
    Which agent is most accurate? Use for ensemble weighting.
    """
    
    # Get all signals with outcomes
    signals = db.query(Signal).join(SignalPerformance).all()
    
    agent_stats = {
        "quant": {"correct": 0, "total": 0},
        "sentiment": {"correct": 0, "total": 0},
        "regime": {"correct": 0, "total": 0}
    }
    
    for signal in signals:
        agent_outputs = signal.reasoning["agent_outputs"]
        actual_outcome = signal.performances[0].outcome
        
        for agent_name, output in agent_outputs.items():
            if agent_name == "risk":
                continue  # Risk agent doesn't predict direction
            
            agent_signal = output["signal"]
            agent_stats[agent_name]["total"] += 1
            
            # Check if agent was correct
            if (agent_signal in ["BUY", "STRONG_BUY"] and actual_outcome == "win") or \
               (agent_signal in ["SELL", "STRONG_SELL"] and actual_outcome == "win"):
                agent_stats[agent_name]["correct"] += 1
    
    # Compute accuracy
    for agent in agent_stats:
        total = agent_stats[agent]["total"]
        if total > 0:
            agent_stats[agent]["accuracy"] = agent_stats[agent]["correct"] / total
    
    return agent_stats
```

### 4. Retraining Trigger Logic
```python
async def check_retraining_triggers():
    """
    Decide if models need retraining.
    """
    
    triggers = []
    
    # Check 1: Accuracy drop
    recent_accuracy = compute_recent_accuracy(days=30)
    if recent_accuracy < 0.55:
        triggers.append({
            "type": "accuracy_drop",
            "value": recent_accuracy,
            "threshold": 0.55
        })
    
    # Check 2: New data accumulation
    new_signals_count = db.count_signals_since_last_training()
    if new_signals_count > 1000:
        triggers.append({
            "type": "new_data",
            "value": new_signals_count,
            "threshold": 1000
        })
    
    # Check 3: Regime shift
    current_regime = detect_current_regime()
    last_training_regime = get_last_training_regime()
    if current_regime != last_training_regime:
        triggers.append({
            "type": "regime_shift",
            "old": last_training_regime,
            "new": current_regime
        })
    
    if triggers:
        # Trigger retraining
        await trigger_model_retraining(triggers)
    
    return triggers
```

## Self-Learning Loop (Full Cycle)

```
1. Signal Generated (Layer 4-5)
   ↓
2. User Executes Trade (or auto-execution via broker API)
   ↓
3. Trade Outcome Logged (win/loss/breakeven)
   ↓
4. Performance Recorded in signal_performance table
   ↓
5. Analytics: Compute win rates, agent accuracy, regime performance
   ↓
6. Signal Intelligence Updated: Which signals work in which regimes?
   ↓
7. Retraining Trigger Check: Is accuracy dropping?
   ↓
8. If Yes: Retrain Quant Agent, Sentiment Agent, Meta-Learner
   ↓
9. A/B Test: New model vs old model (shadow mode)
   ↓
10. Deploy New Model if better
   ↓
11. Repeat (Continuous Improvement)
```

## Performance Metrics

### System-Level
- **Overall win rate:** Target >65%
- **Sharpe ratio:** Target >1.5
- **Max drawdown:** Target <15%
- **Average PnL per signal:** Target >3%

### Agent-Level
- **Quant agent accuracy:** Target >55%
- **Sentiment agent accuracy:** Target >50%
- **Meta-learner accuracy:** Target >60%

### Regime-Level
- **High-vol trending win rate:** Track separately
- **Low-vol ranging win rate:** Track separately
- Adaptive thresholds per regime

## API Endpoints

### GET /api/performance/summary
```json
{
    "overall": {
        "total_signals": 1523,
        "win_rate": 0.67,
        "avg_pnl_percent": 3.8,
        "sharpe_ratio": 1.72,
        "max_drawdown": 0.12
    },
    "by_signal_type": {
        "BUY": {"count": 623, "win_rate": 0.69},
        "SELL": {"count": 421, "win_rate": 0.64},
        "STRONG_BUY": {"count": 289, "win_rate": 0.71}
    },
    "by_regime": {
        "high_vol_trending": {"count": 412, "win_rate": 0.71},
        "low_vol_ranging": {"count": 578, "win_rate": 0.62}
    }
}
```

### GET /api/performance/agents
```json
{
    "quant": {"accuracy": 0.58, "total_predictions": 1523},
    "sentiment": {"accuracy": 0.52, "total_predictions": 1523},
    "regime": {"accuracy": 0.61, "total_predictions": 1523},
    "meta_learner": {"accuracy": 0.67, "total_predictions": 1523}
}
```

## Testing

- Unit tests: Outcome computation, decay detection
- Integration tests: Full learning loop simulation
- Backtesting: Historical self-learning performance
- A/B tests: New model vs old model accuracy

## Acceptance Criteria

- [ ] Signal outcomes tracked automatically
- [ ] Performance analytics compute win rates by signal/regime/agent
- [ ] Retraining triggers work (accuracy drop, new data, regime shift)
- [ ] Self-learning loop runs end-to-end
- [ ] Performance dashboard API returns metrics
- [ ] Celery tasks automate daily/weekly updates

## Next Sprint

**Sprint 07: Broker Integration** - Zerodha Kite API, order placement, portfolio sync

---

**Assigned to:** Sub-agent (performance-memory)  
**Start Date:** TBD (after Sprint 05)  
**Target Completion:** TBD  
