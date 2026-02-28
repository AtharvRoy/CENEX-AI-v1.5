"""Create market data tables for Sprint 02

Revision ID: 002
Revises: 001
Create Date: 2024-02-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create market data tables and populate initial data."""
    
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    
    # Create symbols table
    op.create_table(
        'symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('exchange', sa.String(length=20), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('market_cap', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('idx_symbols_symbol', 'symbols', ['symbol'])
    op.create_index('idx_symbols_is_active', 'symbols', ['is_active'])
    op.create_index('idx_symbols_exchange', 'symbols', ['exchange'])
    
    # Create market_data table
    op.create_table(
        'market_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('high', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('low', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('close', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('adj_close', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('symbol', 'timestamp')
    )
    op.create_index('idx_market_data_symbol', 'market_data', ['symbol'])
    op.create_index('idx_market_data_timestamp', 'market_data', [sa.text('timestamp DESC')])
    op.create_index('idx_market_data_symbol_timestamp', 'market_data', ['symbol', sa.text('timestamp DESC')])
    
    # Convert to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable(
            'market_data',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );
    """)
    
    # Create data_ingestion_log table
    op.create_table(
        'data_ingestion_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('records_inserted', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ingestion_log_symbol', 'data_ingestion_log', ['symbol'])
    op.create_index('idx_ingestion_log_status', 'data_ingestion_log', ['status'])
    op.create_index('idx_ingestion_log_started_at', 'data_ingestion_log', [sa.text('started_at DESC')])
    
    # Insert Nifty 50 symbols
    op.execute("""
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
    """)


def downgrade():
    """Drop market data tables."""
    
    op.drop_index('idx_ingestion_log_started_at', table_name='data_ingestion_log')
    op.drop_index('idx_ingestion_log_status', table_name='data_ingestion_log')
    op.drop_index('idx_ingestion_log_symbol', table_name='data_ingestion_log')
    op.drop_table('data_ingestion_log')
    
    op.drop_index('idx_market_data_symbol_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_symbol', table_name='market_data')
    op.drop_table('market_data')
    
    op.drop_index('idx_symbols_exchange', table_name='symbols')
    op.drop_index('idx_symbols_is_active', table_name='symbols')
    op.drop_index('idx_symbols_symbol', table_name='symbols')
    op.drop_table('symbols')
