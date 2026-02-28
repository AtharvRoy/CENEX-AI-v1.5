# Sprint 01: Backend Foundation

**Duration:** Week 1-2  
**Owner:** Sub-agent TBD  
**Status:** Not Started  

## Goals

Build the FastAPI backend foundation with:
1. Project structure
2. Database setup (PostgreSQL + TimescaleDB)
3. Authentication (JWT)
4. Core models
5. API boilerplate

## Deliverables

### 1. FastAPI Application Setup
- `backend/app/main.py` - FastAPI app entry point
- `backend/app/core/config.py` - Settings (env vars, secrets)
- `backend/app/core/security.py` - JWT auth, password hashing
- `backend/app/core/database.py` - SQLAlchemy session management
- `backend/requirements.txt` - Python dependencies

### 2. Database Schema (SQLAlchemy Models)
- `User` - user accounts, auth, subscription tiers
- `Portfolio` - user portfolios
- `Position` - current positions
- `Signal` - generated signals (buy/sell)
- `Trade` - executed trades
- `SignalPerformance` - outcome tracking (Layer 6)
- `MarketData` - OHLCV + indicators (TimescaleDB hypertable)

### 3. Authentication System
- `/api/auth/register` - user registration
- `/api/auth/login` - JWT token generation
- `/api/auth/refresh` - refresh token
- `/api/auth/me` - current user info
- Middleware: JWT validation

### 4. Core API Routes (Stubs)
- `/api/signals/` - list signals (placeholder)
- `/api/portfolio/` - portfolio data (placeholder)
- `/api/market/` - market data (placeholder)

### 5. Docker Setup
- `Dockerfile` for FastAPI
- `docker-compose.yml` (FastAPI + PostgreSQL + TimescaleDB + Redis)

## Tech Decisions

- **Database:** PostgreSQL 15+ with TimescaleDB extension
- **Auth:** JWT (access + refresh tokens), bcrypt for passwords
- **ORM:** SQLAlchemy 2.0 (async)
- **Validation:** Pydantic v2
- **Environment:** `.env` for secrets (not committed)

## Dependencies

```txt
fastapi[all]>=0.109.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
redis>=5.0.0
celery>=5.3.0
uvicorn[standard]>=0.25.0
```

## Database Schema SQL (Initial)

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free', -- free, premium, pro
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolios table
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    broker VARCHAR(50), -- zerodha, upstox, angel_one
    broker_access_token TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signals table
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL, -- NSE, BSE
    signal_type VARCHAR(20) NOT NULL, -- STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL
    confidence FLOAT NOT NULL, -- 0.0 to 1.0
    price_entry FLOAT,
    price_target FLOAT,
    price_stoploss FLOAT,
    reasoning JSONB, -- agent outputs, feature importance
    regime VARCHAR(50), -- high_vol, low_vol, trending, ranging
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    portfolio_id INTEGER REFERENCES portfolios(id),
    signal_id INTEGER REFERENCES signals(id),
    symbol VARCHAR(50) NOT NULL,
    trade_type VARCHAR(10) NOT NULL, -- BUY, SELL
    quantity INTEGER NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    pnl FLOAT,
    status VARCHAR(20) DEFAULT 'open', -- open, closed, cancelled
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

-- Signal performance (Layer 6 - Performance Memory)
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

-- Market data (TimescaleDB hypertable)
CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (time, symbol, exchange)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('market_data', 'time');

-- Indexes
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_market_data_symbol ON market_data(symbol, time DESC);
```

## Testing

- Unit tests for auth (registration, login, token validation)
- Integration tests for database operations
- API endpoint tests (pytest + TestClient)

## Acceptance Criteria

- [x] FastAPI app runs locally
- [x] Database schema created (PostgreSQL + TimescaleDB)
- [x] User registration + login works
- [x] JWT authentication middleware works
- [x] Docker Compose brings up full stack
- [x] API docs available at `/docs`

## Next Sprint

**Sprint 02: Data Layer** - Market data ingestion, Yahoo Finance integration, caching

---

**Assigned to:** Sub-agent (backend-foundation)  
**Start Date:** 2026-02-28  
**Target Completion:** 2026-03-07  
