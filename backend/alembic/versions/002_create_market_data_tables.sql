-- Migration: Create market data tables
-- Sprint 02: Data Layer
-- Created: 2024-02-28

-- Enable TimescaleDB extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create symbols table
CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    exchange VARCHAR(20) NOT NULL,
    sector VARCHAR(100),
    market_cap BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for symbols
CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols(symbol);
CREATE INDEX IF NOT EXISTS idx_symbols_is_active ON symbols(is_active);
CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols(exchange);

-- Create market_data table (will be converted to hypertable)
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL,
    symbol VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(20, 4) NOT NULL,
    high NUMERIC(20, 4) NOT NULL,
    low NUMERIC(20, 4) NOT NULL,
    close NUMERIC(20, 4) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(20, 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);

-- Create indexes for market_data
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp DESC);

-- Convert market_data to TimescaleDB hypertable
SELECT create_hypertable(
    'market_data',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

-- Create data_ingestion_log table
CREATE TABLE IF NOT EXISTS data_ingestion_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    records_inserted INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Create indexes for data_ingestion_log
CREATE INDEX IF NOT EXISTS idx_ingestion_log_symbol ON data_ingestion_log(symbol);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_status ON data_ingestion_log(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_started_at ON data_ingestion_log(started_at DESC);

-- Insert Nifty 50 symbols
INSERT INTO symbols (symbol, company_name, exchange, sector) VALUES
    ('RELIANCE.NS', 'Reliance Industries', 'NSE', 'Energy'),
    ('TCS.NS', 'Tata Consultancy Services', 'NSE', 'IT'),
    ('HDFCBANK.NS', 'HDFC Bank', 'NSE', 'Banking'),
    ('INFY.NS', 'Infosys', 'NSE', 'IT'),
    ('ICICIBANK.NS', 'ICICI Bank', 'NSE', 'Banking'),
    ('HINDUNILVR.NS', 'Hindustan Unilever', 'NSE', 'FMCG'),
    ('BHARTIARTL.NS', 'Bharti Airtel', 'NSE', 'Telecom'),
    ('ITC.NS', 'ITC Limited', 'NSE', 'FMCG'),
    ('SBIN.NS', 'State Bank of India', 'NSE', 'Banking'),
    ('KOTAKBANK.NS', 'Kotak Mahindra Bank', 'NSE', 'Banking'),
    ('LT.NS', 'Larsen & Toubro', 'NSE', 'Infrastructure'),
    ('AXISBANK.NS', 'Axis Bank', 'NSE', 'Banking'),
    ('BAJFINANCE.NS', 'Bajaj Finance', 'NSE', 'Finance'),
    ('HCLTECH.NS', 'HCL Technologies', 'NSE', 'IT'),
    ('ASIANPAINT.NS', 'Asian Paints', 'NSE', 'Consumer Goods'),
    ('MARUTI.NS', 'Maruti Suzuki', 'NSE', 'Automobile'),
    ('WIPRO.NS', 'Wipro', 'NSE', 'IT'),
    ('ULTRACEMCO.NS', 'UltraTech Cement', 'NSE', 'Cement'),
    ('TITAN.NS', 'Titan Company', 'NSE', 'Consumer Goods'),
    ('SUNPHARMA.NS', 'Sun Pharmaceutical', 'NSE', 'Pharma'),
    ('TECHM.NS', 'Tech Mahindra', 'NSE', 'IT'),
    ('NESTLEIND.NS', 'Nestle India', 'NSE', 'FMCG'),
    ('POWERGRID.NS', 'Power Grid Corporation', 'NSE', 'Power'),
    ('BAJAJFINSV.NS', 'Bajaj Finserv', 'NSE', 'Finance'),
    ('NTPC.NS', 'NTPC Limited', 'NSE', 'Power'),
    ('TATAMOTORS.NS', 'Tata Motors', 'NSE', 'Automobile'),
    ('ONGC.NS', 'Oil & Natural Gas Corporation', 'NSE', 'Energy'),
    ('M&M.NS', 'Mahindra & Mahindra', 'NSE', 'Automobile'),
    ('ADANIPORTS.NS', 'Adani Ports', 'NSE', 'Infrastructure'),
    ('JSWSTEEL.NS', 'JSW Steel', 'NSE', 'Steel'),
    ('TATASTEEL.NS', 'Tata Steel', 'NSE', 'Steel'),
    ('INDUSINDBK.NS', 'IndusInd Bank', 'NSE', 'Banking'),
    ('GRASIM.NS', 'Grasim Industries', 'NSE', 'Cement'),
    ('COALINDIA.NS', 'Coal India', 'NSE', 'Mining'),
    ('DRREDDY.NS', 'Dr. Reddys Laboratories', 'NSE', 'Pharma'),
    ('DIVISLAB.NS', 'Divi''s Laboratories', 'NSE', 'Pharma'),
    ('BRITANNIA.NS', 'Britannia Industries', 'NSE', 'FMCG'),
    ('EICHERMOT.NS', 'Eicher Motors', 'NSE', 'Automobile'),
    ('HINDALCO.NS', 'Hindalco Industries', 'NSE', 'Metals'),
    ('CIPLA.NS', 'Cipla', 'NSE', 'Pharma'),
    ('HEROMOTOCO.NS', 'Hero MotoCorp', 'NSE', 'Automobile'),
    ('APOLLOHOSP.NS', 'Apollo Hospitals', 'NSE', 'Healthcare'),
    ('BPCL.NS', 'Bharat Petroleum', 'NSE', 'Energy'),
    ('SHREECEM.NS', 'Shree Cement', 'NSE', 'Cement'),
    ('TATACONSUM.NS', 'Tata Consumer Products', 'NSE', 'FMCG'),
    ('UPL.NS', 'UPL Limited', 'NSE', 'Chemicals'),
    ('IOC.NS', 'Indian Oil Corporation', 'NSE', 'Energy'),
    ('ADANIENT.NS', 'Adani Enterprises', 'NSE', 'Conglomerate'),
    ('BAJAJ-AUTO.NS', 'Bajaj Auto', 'NSE', 'Automobile'),
    ('SBILIFE.NS', 'SBI Life Insurance', 'NSE', 'Insurance')
ON CONFLICT (symbol) DO NOTHING;

-- Create continuous aggregate for daily OHLCV (for faster queries)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_daily
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('1 day', timestamp) AS day,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume
FROM market_data
GROUP BY symbol, day;

-- Refresh policy for continuous aggregate (refresh last 7 days every hour)
SELECT add_continuous_aggregate_policy('market_data_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Create data retention policy (keep hot data for 3 months)
-- Note: This is commented out for now - enable after confirming warm/cold storage setup
-- SELECT add_retention_policy('market_data', INTERVAL '3 months', if_not_exists => TRUE);

-- Grant permissions (adjust based on your user setup)
-- GRANT SELECT, INSERT, UPDATE ON symbols TO cenex;
-- GRANT SELECT, INSERT ON market_data TO cenex;
-- GRANT SELECT, INSERT, UPDATE ON data_ingestion_log TO cenex;
