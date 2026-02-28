# Sprint 07: Broker Integration (Zerodha Kite API)

**Duration:** Week 13-14  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 05 (Signals ready)

## Goals

Integrate with Zerodha Kite API for:
1. Portfolio sync (fetch positions, holdings)
2. Order placement (buy/sell execution)
3. Real-time price streaming (websockets)
4. OAuth2 authentication flow

Start with **Zerodha only** (most popular in India). Upstox/Angel One in Phase 2.

## Deliverables

### 1. Zerodha Kite Client
- `backend/app/services/brokers/zerodha_client.py`
  - OAuth2 authentication
  - Place orders (market, limit, SL)
  - Fetch positions, holdings
  - Get order status
  - Real-time price feed (websockets)

### 2. Broker Service (Abstract)
- `backend/app/services/brokers/base_broker.py`
  - Abstract interface for all brokers
  - Methods: `place_order()`, `get_positions()`, `get_holdings()`, `authenticate()`
  - Future: Plug in Upstox, Angel One with same interface

### 3. Portfolio Sync Service
- `backend/app/services/portfolio_sync.py`
  - Sync user's broker portfolio to our database
  - Update positions table
  - Fetch real-time balances

### 4. Order Execution Service
- `backend/app/services/order_execution.py`
  - Take a signal → place order via broker API
  - Validate margin, position limits
  - Handle partial fills
  - Log trade to database

### 5. OAuth2 Flow (Zerodha)
- `backend/app/api/endpoints/broker_auth.py`
  - `/api/broker/zerodha/login` - initiate OAuth2 flow
  - `/api/broker/zerodha/callback` - handle redirect
  - Store access token encrypted in database

### 6. API Endpoints
- `POST /api/broker/connect` - connect broker account
- `GET /api/broker/positions` - fetch current positions
- `GET /api/broker/holdings` - fetch holdings
- `POST /api/broker/order` - place order
- `GET /api/broker/orders` - order history
- `POST /api/signals/{signal_id}/execute` - auto-execute a signal

## Tech Stack

- **Kite Connect:** Official Zerodha Python SDK (`kiteconnect`)
- **Encryption:** Fernet (for access tokens)
- **WebSockets:** For real-time price streaming

## Dependencies

```txt
kiteconnect>=4.3.0
cryptography>=41.0.0
websocket-client>=1.6.0
```

## Zerodha Kite API Setup

### 1. Create Kite Connect App
1. Go to https://developers.kite.trade/
2. Create app → Get **API Key** and **API Secret**
3. Set redirect URL: `https://yourdomain.com/api/broker/zerodha/callback`

### 2. OAuth2 Flow
```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="YOUR_API_KEY")

# Step 1: Generate login URL
login_url = kite.login_url()
# Redirect user to login_url

# Step 2: User logs in, Zerodha redirects to callback with request_token
# GET /api/broker/zerodha/callback?request_token=xxx&status=success

# Step 3: Exchange request_token for access_token
data = kite.generate_session(request_token, api_secret="YOUR_API_SECRET")
access_token = data["access_token"]

# Step 4: Store access_token (encrypted) in database
kite.set_access_token(access_token)
```

### 3. Place Order Example
```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="YOUR_API_KEY")
kite.set_access_token(user_access_token)

# Place market order
order_id = kite.place_order(
    variety=kite.VARIETY_REGULAR,
    exchange=kite.EXCHANGE_NSE,
    tradingsymbol="RELIANCE",
    transaction_type=kite.TRANSACTION_TYPE_BUY,
    quantity=10,
    product=kite.PRODUCT_MIS,  # Intraday
    order_type=kite.ORDER_TYPE_MARKET
)

print(f"Order placed: {order_id}")
```

### 4. Fetch Positions
```python
positions = kite.positions()

# Net positions
for position in positions["net"]:
    print(f"{position['tradingsymbol']}: {position['quantity']} @ {position['average_price']}")
```

## Order Execution Flow

```
1. User receives signal (BUY RELIANCE @ 2850, Target: 2900, SL: 2750)
   ↓
2. User clicks "Execute Trade" in UI
   ↓
3. Backend validates:
   - User has connected broker account
   - Sufficient margin/balance
   - Signal is still valid (<5 min old)
   ↓
4. Compute position size (Risk Agent logic: 5% of portfolio)
   ↓
5. Place order via Zerodha API
   ↓
6. Log trade to database (trades table)
   ↓
7. Return order confirmation to user
   ↓
8. Monitor order status (filled/rejected/pending)
   ↓
9. Update trade status in database
```

## Risk Management (OMS/RMS)

### Order Management System (OMS)
```python
async def place_order_with_validation(user_id, signal, quantity):
    """
    Place order with margin validation and position limits.
    """
    
    user = await db.get_user(user_id)
    portfolio = await db.get_portfolio(user_id)
    
    # Check 1: Broker connected
    if not portfolio.broker_access_token:
        raise Exception("Broker not connected")
    
    # Check 2: Margin available
    available_margin = kite.margins()["equity"]["available"]["cash"]
    required_margin = signal.price_entry * quantity
    
    if required_margin > available_margin:
        raise Exception("Insufficient margin")
    
    # Check 3: Position limits (max 10% per symbol)
    portfolio_value = compute_portfolio_value(portfolio)
    max_position_value = portfolio_value * 0.10
    
    if signal.price_entry * quantity > max_position_value:
        raise Exception("Exceeds position limit")
    
    # Check 4: Daily loss limit (max -5% per day)
    daily_pnl = compute_daily_pnl(user_id)
    if daily_pnl < -0.05 * portfolio_value:
        raise Exception("Daily loss limit reached")
    
    # All checks passed → place order
    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=signal.exchange,
        tradingsymbol=signal.symbol.replace(".NS", ""),
        transaction_type=kite.TRANSACTION_TYPE_BUY if signal.signal_type in ["BUY", "STRONG_BUY"] else kite.TRANSACTION_TYPE_SELL,
        quantity=quantity,
        product=kite.PRODUCT_CNC,  # Delivery (or MIS for intraday)
        order_type=kite.ORDER_TYPE_LIMIT,
        price=signal.price_entry
    )
    
    # Log trade
    trade = Trade(
        user_id=user_id,
        portfolio_id=portfolio.id,
        signal_id=signal.id,
        symbol=signal.symbol,
        trade_type="BUY" if signal.signal_type in ["BUY", "STRONG_BUY"] else "SELL",
        quantity=quantity,
        entry_price=signal.price_entry,
        status="pending"
    )
    await db.save(trade)
    
    return {"order_id": order_id, "trade_id": trade.id}
```

## WebSocket Price Streaming (Real-Time)

```python
from kiteconnect import KiteTicker

kws = KiteTicker(api_key, access_token)

def on_ticks(ws, ticks):
    """Handle real-time price updates."""
    for tick in ticks:
        symbol = tick["instrument_token"]
        ltp = tick["last_price"]
        
        # Update cache
        redis.set(f"price:{symbol}", ltp, ex=60)
        
        # Check stop-loss / target
        check_trade_alerts(symbol, ltp)

def on_connect(ws, response):
    """Subscribe to instruments on connect."""
    ws.subscribe([738561])  # RELIANCE token
    ws.set_mode(ws.MODE_LTP, [738561])

kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.connect(threaded=True)
```

## Database Schema Updates

```sql
-- Add broker fields to portfolios table (already defined in Sprint 01)
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS broker_user_id VARCHAR(100);
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS broker_encrypted_token TEXT;
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS broker_token_expires_at TIMESTAMPTZ;
```

## API Endpoints

### POST /api/broker/connect
```json
Request:
{
    "broker": "zerodha",
    "request_token": "xxx"  # From OAuth callback
}

Response:
{
    "status": "connected",
    "portfolio_id": 123,
    "available_margin": 50000
}
```

### POST /api/signals/{signal_id}/execute
```json
Request:
{
    "quantity": 10  # Optional (default: auto-compute via Risk Agent)
}

Response:
{
    "order_id": "240228000123456",
    "trade_id": 789,
    "status": "pending",
    "symbol": "RELIANCE",
    "quantity": 10,
    "price": 2850,
    "estimated_cost": 28500
}
```

## Testing

- Unit tests: Order validation logic
- Integration tests: Mock Zerodha API calls
- Sandbox testing: Zerodha provides sandbox environment
- Paper trading: Simulate orders without real money

## Security

- **Encrypt access tokens** (Fernet) before storing in database
- **HTTPS only** for OAuth callbacks
- **Rate limiting** on order endpoints
- **Audit logging** for all order placements

## Performance Targets

- **Order placement latency:** <500ms
- **Portfolio sync:** <2 seconds
- **WebSocket latency:** <100ms (real-time prices)

## Acceptance Criteria

- [ ] OAuth2 flow works (user can connect Zerodha account)
- [ ] Portfolio positions sync correctly
- [ ] Orders can be placed via API
- [ ] Risk validation prevents over-trading
- [ ] Trades logged to database
- [ ] Real-time price streaming works

## Next Sprint

**Sprint 08: Frontend (Next.js Dashboard)** - UI for signals, portfolio, trading

---

**Assigned to:** Sub-agent (broker-integration)  
**Start Date:** TBD (after Sprint 05)  
**Target Completion:** TBD  
