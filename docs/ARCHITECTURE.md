# Cenex AI - System Architecture

## Overview
Cenex AI is an institutional-grade AI financial intelligence and smart brokerage platform built on a 6-layer architecture with self-learning capabilities.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Next.js Frontend  │  Mobile App (Future)  │  API Clients           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI  │  JWT Auth  │  Rate Limiting  │  Request Validation      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   LAYER 1:    │  │   LAYER 2:    │  │   LAYER 3:    │
│  DATA LAYER   │  │   FEATURE     │  │  MULTI-AGENT  │
│               │  │   FACTORY     │  │  INTELLIGENCE │
├───────────────┤  ├───────────────┤  ├───────────────┤
│ Yahoo Finance │  │ Technical:    │  │ 🧮 Quant      │
│ NSE/BSE APIs  │  │ - RSI, MACD   │  │   Agent       │
│ News (RSS)    │  │ - Bollinger   │  │               │
│ Macro (FRED)  │  │ - ATR, ADX    │  │ 📰 Sentiment  │
│               │  │ - VWAP, OBV   │  │   Agent       │
│ Storage:      │  │               │  │               │
│ - TimescaleDB │  │ Regime:       │  │ 🌍 Regime     │
│ - Parquet/R2  │  │ - Volatility  │  │   Agent       │
│ - Redis Cache │  │ - HMM         │  │               │
│               │  │               │  │ ⚠️  Risk      │
│ HOT: 3mo DB   │  │ Narrative:    │  │   Agent       │
│ WARM: 2yr R2  │  │ - FinBERT     │  │               │
│ COLD: Archive │  │ - Sentiment   │  │               │
│               │  │               │  │ Models:       │
│               │  │ Macro:        │  │ - LightGBM    │
│               │  │ - Yield curve │  │ - XGBoost     │
│               │  │ - Inflation   │  │ - LSTM        │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │        LAYER 4: META DECISION        │
        │            ENGINE                    │
        ├──────────────────────────────────────┤
        │ • Logistic Stacking                  │
        │ • Confidence Calibration (Platt)     │
        │ • Meta-Labeling                      │
        │                                      │
        │ Output:                              │
        │ STRONG BUY | BUY | HOLD |            │
        │ SELL | STRONG SELL | NO SIGNAL       │
        └──────────────────┬───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │   LAYER 5: SIGNAL QUALITY ENGINE     │
        ├──────────────────────────────────────┤
        │ • Regime-aware filtering             │
        │ • Volatility anomaly detection       │
        │ • Historical signal decay analysis   │
        │ • Liquidity checks                   │
        │                                      │
        │ Gate: Confidence > 80% + Risk OK     │
        └──────────────────┬───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │   LAYER 6: PERFORMANCE MEMORY        │
        │      (Self-Learning Loop)            │
        ├──────────────────────────────────────┤
        │ • Trade outcome logging              │
        │ • Regime-specific performance        │
        │ • Signal decay tracking              │
        │ • Model retraining triggers          │
        │                                      │
        │ → Proprietary Intelligence Moat      │
        └──────────────────┬───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │     EXECUTION & BROKERAGE LAYER      │
        ├──────────────────────────────────────┤
        │  OMS (Order Management System)       │
        │  • Margin validation                 │
        │  • Position limit checks             │
        │  • Order placement                   │
        │                                      │
        │  RMS (Risk Management System)        │
        │  • Daily loss limits                 │
        │  • Exposure caps                     │
        │  • Circuit breakers                  │
        │                                      │
        │  Smart Order Router                  │
        │  • Best execution                    │
        │  • Slippage minimization             │
        │  • Partial fill handling             │
        │                                      │
        │  Broker Integration:                 │
        │  ├─ Zerodha Kite API                 │
        │  ├─ Upstox API                       │
        │  └─ Angel One API                    │
        │                                      │
        │  Future: Direct Brokerage            │
        │  (SEBI registration required)        │
        └──────────────────┬───────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │         NOTIFICATION LAYER           │
        ├──────────────────────────────────────┤
        │  • SMS (Twilio)                      │
        │  • Email (SendGrid)                  │
        │  • Push Notifications                │
        │  • Webhooks                          │
        │                                      │
        │  Trigger: Signal + Confidence > 80%  │
        └──────────────────────────────────────┘
```

---

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Task Queue:** Celery + Redis
- **ML Stack:** scikit-learn, LightGBM, XGBoost, PyTorch, Transformers (FinBERT)

### Data Storage
- **Time-Series DB:** PostgreSQL + TimescaleDB extension
- **Object Storage:** Cloudflare R2 (Parquet files)
- **Cache:** Redis
- **Hot Data:** 3 months in TimescaleDB
- **Warm Data:** 2 years in R2 (Parquet)
- **Cold Data:** Archived in R2

### Frontend
- **Framework:** Next.js 14+ (React)
- **Styling:** TailwindCSS
- **Charts:** Recharts / Plotly
- **State:** Zustand / React Query

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Hosting:** Railway / Render / AWS
- **CDN:** Cloudflare
- **CI/CD:** GitHub Actions

---

## Data Flow

### Signal Generation Flow
```
Market Data → Feature Computation → Multi-Agent Analysis → 
Meta Decision → Signal Quality Gate → Final Signal → 
Notification / Execution
```

### Trade Execution Flow
```
Signal → Risk Validation → OMS → Broker API → 
Exchange → Confirmation → Portfolio Update → 
Performance Memory
```

### Learning Loop
```
Trade Outcome → Performance Analysis → 
Regime Classification → Signal Intelligence Update → 
Model Retraining (if needed)
```

---

## Security & Compliance

### Authentication
- JWT tokens (access + refresh)
- 2FA (TOTP)
- OAuth2 for broker connections

### Data Security
- Encrypted credentials (Fernet)
- HTTPS only
- API key rotation
- Audit logging

### Compliance
- KYC verification
- AML checks
- SEBI compliance (Phase 2)
- PCI-DSS (future payment processing)

---

## Scalability Considerations

### MVP Scale (First 1000 users)
- Single FastAPI instance
- PostgreSQL (managed)
- Redis cache
- R2 storage
- **Cost:** ~$50–100/month

### Growth Scale (10,000+ users)
- Horizontal FastAPI scaling (load balancer)
- PostgreSQL read replicas
- Redis cluster
- Celery workers (distributed)
- **Cost:** ~$500–1000/month

### Enterprise Scale (100,000+ users)
- Kubernetes orchestration
- Multi-region deployment
- Dedicated ML inference servers
- CDN optimization
- **Cost:** Custom enterprise pricing

---

## Monitoring & Observability

- **Logging:** Structured JSON logs (Elasticsearch + Kibana future)
- **Metrics:** Prometheus + Grafana
- **Error Tracking:** Sentry
- **APM:** DataDog (future)

### Key Metrics
- Signal generation latency
- Model prediction time
- Trade execution latency
- API response times
- Cache hit rates
- Model accuracy by regime

---

## Disaster Recovery

- **Database:** Daily automated backups (7-day retention)
- **Object Storage:** Versioning enabled
- **Incident Response:** Documented runbooks
- **RTO:** 4 hours
- **RPO:** 24 hours

---

## Product Tiers

### 🆓 Free
- 5 core indicators
- 2 markets (NSE, BSE)
- Limited signals (5/day)
- Basic portfolio tracking
- No brokerage execution

### 🟡 Premium ($49/month or ₹3999/month)
- Full multi-agent AI
- All markets
- Unlimited signals
- Real-time risk intelligence
- Broker integration (trade execution)
- Portfolio AI optimization
- Explainability dashboard
- No ads
- Priority support

### 🟣 Pro (Future - $199/month)
- Everything in Premium
- API access
- Strategy automation
- Advanced backtesting engine
- Custom order types
- AI trade avoidance
- Institutional analytics
- Dedicated support

---

## Competitive Moat

### What Makes Cenex Defensible:

1. **Performance Memory Database**
   - Proprietary signal performance history
   - Regime-specific intelligence
   - Continuously improving

2. **Signal Quality Engine**
   - Not just signals, but validated signals
   - Regime-aware filtering
   - Reduces noise by 60%+

3. **Self-Learning Loop**
   - Models improve from own outcomes
   - No manual retraining needed
   - Adaptive to market conditions

4. **Risk-First Design**
   - Not max profit, max risk-adjusted returns
   - Institutional-grade position sizing
   - Monte Carlo simulations

This is NOT replicable with:
- GPT wrapper
- Basic indicators
- Generic ML models

---

## Success Metrics

### Signal Performance
- Win rate: 60–65% (realistic)
- Risk-reward ratio: 1.8–2.5
- Sharpe ratio: >1.5
- Max drawdown: <15%

### User Metrics
- Daily active users
- Signal→Trade conversion rate
- Average portfolio return
- Churn rate
- NPS score

### Technical Metrics
- 99.5% uptime
- <200ms API response time
- <5s signal generation time
- <500ms trade execution latency

---

## Roadmap

### Phase 1 (MVP) - Months 1-4
- Core signal engine
- Broker integration
- Free + Premium tiers
- Web app

### Phase 2 - Months 5-8
- Advanced regime detection
- Monte Carlo risk engine
- Mobile app
- API access (Pro tier)

### Phase 3 - Months 9-12
- Strategy automation
- Backtesting engine
- Options AI
- Performance analytics v2

### Phase 4 - Year 2
- Direct brokerage (SEBI)
- Global markets (US, EU)
- Institutional API
- Wealth management integration

---

**This architecture is built for perfection, not speed.**

Every layer has a clear purpose.
Every component is testable.
Every decision is defensible.

Next: Database schema design.
