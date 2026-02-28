# Sprint 02: Data Layer

**Duration:** Week 3-4  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 01 (Backend Foundation)

## Goals

Build the data ingestion pipeline for market data:
1. Yahoo Finance integration (primary source)
2. NSE/BSE data fallback (future)
3. News feed ingestion (RSS)
4. Macro data (FRED API - future)
5. TimescaleDB storage with hot/warm/cold tiers
6. Redis caching layer
7. Scheduled data updates (Celery tasks)

## Deliverables

### 1. Market Data Service
- `backend/app/services/market_data.py`
  - Fetch OHLCV data (Yahoo Finance)
  - Store in TimescaleDB
  - Cache recent data in Redis
  - Handle missing data gracefully

### 2. Data Ingestion Pipeline
- `backend/app/services/data_ingestion.py`
  - Historical data backfill (3 months hot, 2 years warm)
  - Incremental updates (every 15 minutes during market hours)
  - Retry logic and error handling
  - Data validation

### 3. Celery Tasks
- `backend/app/tasks/market_data_tasks.py`
  - `update_market_data()` - scheduled every 15 minutes
  - `backfill_historical_data(symbol, days)` - manual trigger
  - `export_to_parquet()` - warm data → R2 (future)

### 4. API Endpoints
- `GET /api/market/{symbol}/ohlcv` - get OHLCV data (timeframe, range)
- `GET /api/market/{symbol}/latest` - latest price
- `GET /api/market/watchlist` - multiple symbols at once
- `POST /api/admin/backfill` - trigger historical backfill (admin only)

### 5. Data Storage Architecture
- **Hot Data (3 months):** TimescaleDB
- **Warm Data (2 years):** Parquet → Cloudflare R2 (Phase 2)
- **Cold Data:** Archived (Phase 3)

### 6. Symbol Universe
- Initial support: Nifty 50 + Bank Nifty stocks (50 symbols)
- Expandable to full NSE/BSE (future)
- Symbol metadata table (company name, sector, market cap)

## Tech Stack

- **Data Source:** Yahoo Finance API (yfinance library)
- **Storage:** TimescaleDB (hypertable for time-series)
- **Cache:** Redis (5-minute TTL for latest prices)
- **Task Queue:** Celery + Redis (scheduled updates)
- **Future:** NSE/BSE official APIs, FRED for macro data

## Dependencies

```txt
yfinance>=0.2.36
pandas>=2.1.0
numpy>=1.24.0
celery[redis]>=5.3.0
redis>=5.0.0
requests>=2.31.0
```

## Database Schema (Additional Tables)

```sql
-- Symbol metadata
CREATE TABLE symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    exchange VARCHAR(20) NOT NULL, -- NSE, BSE
    sector VARCHAR(100),
    market_cap BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data ingestion log
CREATE TABLE data_ingestion_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL, -- yahoo, nse, bse
    records_inserted INTEGER,
    status VARCHAR(20), -- success, partial, failed
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Insert Nifty 50 symbols (sample)
INSERT INTO symbols (symbol, company_name, exchange, sector) VALUES
('RELIANCE.NS', 'Reliance Industries', 'NSE', 'Energy'),
('TCS.NS', 'Tata Consultancy Services', 'NSE', 'IT'),
('HDFCBANK.NS', 'HDFC Bank', 'NSE', 'Banking'),
('INFY.NS', 'Infosys', 'NSE', 'IT'),
('ICICIBANK.NS', 'ICICI Bank', 'NSE', 'Banking');
-- (add remaining 45)
```

## Data Validation

- **Price sanity checks:** Open/High/Low/Close relationships
- **Volume anomaly detection:** >10x average = flag for review
- **Gap detection:** Missing timestamps during market hours
- **Duplicate prevention:** Upsert logic (ON CONFLICT)

## Celery Beat Schedule

```python
# backend/app/core/celery_config.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'update-market-data': {
        'task': 'app.tasks.market_data_tasks.update_market_data',
        'schedule': crontab(minute='*/15', hour='9-15', day_of_week='mon-fri'),  # Market hours
    },
    'cleanup-old-cache': {
        'task': 'app.tasks.maintenance_tasks.cleanup_redis_cache',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

## Testing

- Unit tests: Yahoo Finance data parsing
- Integration tests: TimescaleDB insert/query
- Cache tests: Redis hit/miss scenarios
- Task tests: Celery task execution

## Performance Targets

- **Ingestion speed:** 1000 OHLCV records/second
- **API latency:** <100ms for cached data, <500ms for DB query
- **Cache hit rate:** >80% during market hours
- **Data freshness:** <5 minutes delay

## Acceptance Criteria

- [ ] Historical data backfill works (3 months for Nifty 50)
- [ ] Scheduled updates run every 15 minutes during market hours
- [ ] Redis cache speeds up repeated queries
- [ ] API endpoints return valid OHLCV data
- [ ] Data validation catches anomalies
- [ ] Celery tasks log success/failure

## Next Sprint

**Sprint 03: Feature Factory** - Technical indicators (RSI, MACD, Bollinger, etc.)

---

**Assigned to:** Sub-agent (data-layer)  
**Start Date:** TBD (after Sprint 01)  
**Target Completion:** TBD  
